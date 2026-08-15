from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from packages.mercator.normalization import classify_freshness, normalize_commodity, normalize_unit
from packages.mercator.providers import EconomicProviderResult, EconomicRequest
from packages.provenance import ProvenanceRecord, content_hash


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _numeric(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        # NASS/AMS use "(D)", "(Z)", "(NA)" for suppressed or unavailable cells.
        return None


def _publication_date(row: dict) -> str | None:
    for key in ("load_time", "end_code_desc", "begin_code_desc"):
        value = row.get(key)
        if value:
            iso = _iso_date(value)
            if iso:
                return iso
    year = str(row.get("year") or "").strip()
    return f"{year}-12-31" if year.isdigit() else None


def _iso_date(value) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text[: len(pattern) + 6], pattern).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _row_geography(row: dict, requested: dict) -> dict:
    geography = dict(requested)
    state_code = str(row.get("state_alpha") or "").strip()
    county = str(row.get("county_name") or "").strip()
    if state_code:
        geography["state_code"] = state_code
    if county:
        geography["county_or_district"] = county.title()
    elif row.get("agg_level_desc") and str(row["agg_level_desc"]).upper() != "COUNTY":
        # Quick Stats answered at a coarser level than requested; say so
        # rather than implying the number is county-specific.
        geography.pop("county_or_district", None)
        geography.pop("county_fips", None)
        geography["state_level_fallback"] = True
    return geography


def _record_id(row: dict) -> str:
    parts = [
        str(row.get("commodity_desc") or "commodity").strip().lower().replace(" ", "-"),
        str(row.get("statisticcat_desc") or "stat").strip().lower().replace(" ", "-"),
        str(row.get("state_alpha") or "us").strip().lower(),
        str(row.get("county_name") or "").strip().lower().replace(" ", "-"),
        str(row.get("year") or "").strip(),
    ]
    return "nass-" + "-".join(part for part in parts if part)


def _redact_key(url: str) -> str:
    # The API key must never reach a persisted provenance record.
    parsed = urllib.parse.urlsplit(url)
    query = [(key, "REDACTED" if key == "key" else value) for key, value in urllib.parse.parse_qsl(parsed.query)]
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))


def _basic_auth_handler(url: str, api_key: str) -> urllib.request.HTTPBasicAuthHandler:
    manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    manager.add_password(None, url, api_key, "")
    return urllib.request.HTTPBasicAuthHandler(manager)


class NASSQuickStatsProvider:
    provider_id = "usda-nass"

    def __init__(self, *, api_key_env: str = "GAIA_NASS_API_KEY", timeout_seconds: float = 10.0) -> None:
        super().__init__()
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds

    async def production(self, request: EconomicRequest) -> EconomicProviderResult:
        # Both names are documented in .env.example; accept either.
        api_key = _first_env(self.api_key_env, "USDA_NASS_API_KEY")
        if not api_key:
            return EconomicProviderResult(status="UNAVAILABLE", warnings=["nass_api_key_not_configured"])
        return await asyncio.to_thread(self._production_sync, request, api_key)

    def _production_sync(self, request: EconomicRequest, api_key: str) -> EconomicProviderResult:
        url = self.request_url(request, api_key)
        try:
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Quick Stats answers 400 when a query matches no rows.
            if exc.code == 400:
                return EconomicProviderResult(status="UNAVAILABLE", warnings=["nass_query_matched_no_records"])
            return EconomicProviderResult(status="PROVIDER_ERROR", warnings=[f"nass_http_{exc.code}"])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return EconomicProviderResult(status="PROVIDER_ERROR", warnings=[f"nass_error:{exc.__class__.__name__}"])
        return self.normalize_production_response(request, payload, _redact_key(url))

    def request_url(self, request: EconomicRequest, api_key: str) -> str:
        params = {
            "key": api_key,
            "format": "JSON",
            "commodity_desc": request.commodity.upper(),
            "year__GE": request.periods[0] if request.periods else "2020",
            "statisticcat_desc": "PRODUCTION",
            "agg_level_desc": "COUNTY" if request.geography.get("county_fips") else "STATE",
        }
        state = request.geography.get("state_code")
        if state:
            params["state_alpha"] = str(state)
        county_fips = str(request.geography.get("county_fips") or "")
        if len(county_fips) == 5:
            # Quick Stats keys county by its 3-digit ANSI code, not the 5-digit FIPS.
            params["county_ansi"] = county_fips[2:]
        return "https://quickstats.nass.usda.gov/api/api_GET/?" + urllib.parse.urlencode(params)

    def normalize_production_response(self, request: EconomicRequest, payload: dict, url: str | None = None) -> EconomicProviderResult:
        rows = payload.get("data") or []
        if not rows:
            return EconomicProviderResult(status="UNAVAILABLE", warnings=["nass_query_matched_no_records"])
        commodity = normalize_commodity(request.commodity, crop_or_taxon=request.crop_or_taxon)
        statistics = []
        for row in rows:
            value = _numeric(row.get("Value"))
            if value is None:
                # NASS suppresses disclosure-restricted cells as "(D)"/"(Z)".
                continue
            period = str(row.get("year") or "")
            publication_date = _publication_date(row)
            unit = str(row.get("unit_desc") or "").strip() or "unknown"
            statistics.append(
                {
                    "statistic": str(row.get("statisticcat_desc") or "production").strip().lower(),
                    "commodity": commodity,
                    "value": value,
                    "unit": unit,
                    "unit_context": normalize_unit(value, unit),
                    "geography": _row_geography(row, request.geography),
                    "observation_period": period,
                    "publication_date": publication_date,
                    "data_class": "RECENT_PERIODIC_STATISTIC",
                    "freshness": classify_freshness("RECENT_PERIODIC_STATISTIC", period, publication_date),
                    "source_native_label": str(row.get("short_desc") or row.get("commodity_desc") or "").strip(),
                    "provider_record_id": _record_id(row),
                    "limitations": ["Periodic NASS statistic; not current crop availability or a price forecast."],
                }
            )
        if not statistics:
            return EconomicProviderResult(status="UNAVAILABLE", warnings=["nass_values_suppressed_or_non_numeric"])
        return EconomicProviderResult(
            status="AVAILABLE",
            data={"production_statistics": statistics},
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=statistics[0]["provider_record_id"],
                    canonical_url=url or "https://quickstats.nass.usda.gov/api",
                    authority="USDA National Agricultural Statistics Service",
                    geographic_scope="US agricultural statistics",
                    license="public domain (U.S. federal government work)",
                    attribution="USDA NASS Quick Stats",
                    content_hash=content_hash(payload),
                )
            ],
            freshness=statistics[0]["freshness"],
        )

    async def market_reports(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["nass_market_reports_not_supported"])

    async def prices(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["nass_prices_not_supported"])

    async def regional_context(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["nass_live_regional_context_normalization_deferred"])

    async def supply_chain(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["nass_supply_chain_not_supported"])


class AMSMyMarketNewsProvider:
    provider_id = "usda-ams"

    def __init__(
        self,
        *,
        api_key_env: str = "GAIA_AMS_API_KEY",
        base_url: str = "https://marsapi.ams.usda.gov",
        report_slug: str = "2651",
        user_agent: str = "GAIA Local Alpha/0.1",
        timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__()
        self.api_key_env = api_key_env
        self.base_url = base_url.rstrip("/")
        # 2651 is the National Fruit and Vegetable Terminal Market report.
        self.report_slug = report_slug
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    async def market_reports(self, request: EconomicRequest) -> EconomicProviderResult:
        api_key = _first_env(self.api_key_env, "USDA_AMS_API_KEY")
        if not api_key:
            return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_api_key_not_configured"])
        return await asyncio.to_thread(self._market_reports_sync, request, api_key)

    def _market_reports_sync(self, request: EconomicRequest, api_key: str) -> EconomicProviderResult:
        url = self.request_url(request)
        # MyMarketNews authenticates with the API key as HTTP Basic username.
        opener = urllib.request.build_opener(_basic_auth_handler(url, api_key))
        http_request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": self.user_agent})
        try:
            with opener.open(http_request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return EconomicProviderResult(status="PROVIDER_ERROR", warnings=[f"ams_http_{exc.code}"])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return EconomicProviderResult(status="PROVIDER_ERROR", warnings=[f"ams_error:{exc.__class__.__name__}"])
        return self.normalize_market_response(request, payload, url)

    def request_url(self, request: EconomicRequest) -> str:
        params = {"q": f"commodity={request.commodity.lower()}", "allSections": "true"}
        return f"{self.base_url}/services/v1.2/reports/{self.report_slug}?" + urllib.parse.urlencode(params)

    def normalize_market_response(self, request: EconomicRequest, payload: dict, url: str | None = None) -> EconomicProviderResult:
        rows = payload.get("results") if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or not rows:
            return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_report_matched_no_observations"])
        commodity = normalize_commodity(request.commodity, crop_or_taxon=request.crop_or_taxon)
        observations = []
        for row in rows:
            value = _numeric(row.get("avg_price") or row.get("mostly_low_price") or row.get("low_price"))
            if value is None:
                continue
            report_date = _iso_date(row.get("report_date") or row.get("report_begin_date"))
            package = str(row.get("package") or "").strip() or None
            grade = str(row.get("grade") or row.get("quality") or "").strip() or None
            unit = f"$/{package}" if package else "$/lb"
            observation = {
                "market": str(row.get("market_location_name") or request.market_region or "USDA AMS market").strip(),
                "commodity": commodity,
                "report_date": report_date,
                "publication_date": report_date,
                "value": value,
                "unit": unit,
                "unit_context": normalize_unit(value, unit, package=package, grade=grade),
                "package": package,
                "grade": grade,
                "currency": "USD",
                "currency_date_context": report_date,
                "geography": request.geography,
                "data_class": "REALTIME_OR_CURRENT_REPORT",
                "freshness": classify_freshness("REALTIME_OR_CURRENT_REPORT", report_date, report_date),
                "source_report": str(row.get("report_title") or self.report_slug),
                "provider_record_id": f"ams-{self.report_slug}-{report_date}-{row.get('market_location_code') or row.get('market_location_name') or 'unknown'}",
                "limitations": ["Market report observation; not a price forecast or trading signal."],
            }
            observations.append(observation)
        if not observations:
            return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_observations_missing_numeric_prices"])
        return EconomicProviderResult(
            status="AVAILABLE",
            data={"market_reports": observations, "price_observations": observations},
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=observations[0]["provider_record_id"],
                    canonical_url=url or f"{self.base_url}/mymarketnews-api",
                    authority="USDA Agricultural Marketing Service",
                    geographic_scope="US market reports",
                    license="public domain (U.S. federal government work)",
                    attribution="USDA AMS MyMarketNews",
                    content_hash=content_hash(payload),
                )
            ],
            freshness=observations[0]["freshness"],
        )

    async def production(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_production_not_supported"])

    async def prices(self, request: EconomicRequest) -> EconomicProviderResult:
        return await self.market_reports(request)

    async def regional_context(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_regional_context_not_supported"])

    async def supply_chain(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_live_supply_chain_normalization_deferred"])
