from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import urllib.error
import urllib.parse
import urllib.request

from packages.environment.providers import EnvironmentalProviderResult
from packages.provenance import ProvenanceRecord, content_hash


NASA_POWER_MISSING_VALUES = {-999, -999.0, -9999, -9999.0}


class NWSApiAdapter:
    provider_id = "nws"
    base_url = "https://api.weather.gov"

    def __init__(self, user_agent: str, timeout_seconds: int = 10) -> None:
        if not user_agent:
            raise ValueError("NWS requires a configured User-Agent")
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    async def forecast(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        try:
            point = self._get_json(f"{self.base_url}/points/{latitude},{longitude}")
            forecast_url = point["properties"]["forecast"]
            forecast = self._get_json(forecast_url)
        except (KeyError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return EnvironmentalProviderResult(status="PROVIDER_ERROR", warnings=[f"nws_error:{exc.__class__.__name__}"])
        return self.normalize_forecast(forecast, forecast_url)

    def normalize_forecast(self, forecast: dict, canonical_url: str) -> EnvironmentalProviderResult:
        period = (forecast.get("properties", {}).get("periods") or [{}])[0]
        data = {
            "temperature": {
                "value": period.get("temperature"),
                "unit": period.get("temperatureUnit"),
                "original_value": period.get("temperature"),
                "original_unit": period.get("temperatureUnit"),
                "evidence_type": "FORECAST",
            },
            "precipitation_probability": {
                "value": (period.get("probabilityOfPrecipitation") or {}).get("value"),
                "unit": "%",
                "evidence_type": "FORECAST",
            },
            "humidity": {"value": (period.get("relativeHumidity") or {}).get("value"), "unit": "%", "evidence_type": "FORECAST"},
            "wind": {"speed": period.get("windSpeed"), "direction": period.get("windDirection"), "evidence_type": "FORECAST"},
            "valid_at": period.get("startTime"),
            "retrieved_at": forecast.get("properties", {}).get("generatedAt"),
            "alerts": [],
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    canonical_url=canonical_url,
                    authority="NOAA/National Weather Service",
                    valid_at=data["valid_at"],
                    geographic_scope="NWS grid forecast",
                    license="public-domain-us-government",
                    attribution="NOAA/NWS",
                    content_hash=content_hash(forecast),
                )
            ],
        )

    def _get_json(self, url: str) -> dict:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/geo+json"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class NASAPowerApiAdapter:
    provider_id = "nasa-power"
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    def __init__(self, base_url: str | None = None, timeout_seconds: int = 15) -> None:
        if base_url:
            base = base_url.rstrip("/")
            self.base_url = base if base.endswith("/point") else f"{base}/api/temporal/daily/point"
        self.timeout_seconds = timeout_seconds

    async def climate_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        power_date = _power_date(at_time)
        params = {
            "parameters": "T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
            "community": "AG",
            "longitude": f"{longitude:.4f}",
            "latitude": f"{latitude:.4f}",
            "start": power_date,
            "end": power_date,
            "format": "JSON",
        }
        url = self.base_url + "?" + urllib.parse.urlencode(params)
        try:
            payload = await asyncio.to_thread(self._get_json, url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return EnvironmentalProviderResult(status="PROVIDER_ERROR", warnings=[f"nasa_power_error:{exc.__class__.__name__}"])
        return self.normalize_daily_response(payload, url)

    def normalize_daily_response(self, payload: dict, canonical_url: str) -> EnvironmentalProviderResult:
        properties = payload.get("properties", {})
        parameters = properties.get("parameter", {})
        data = {
            "temperature_history": {"value": _first_value(parameters.get("T2M", {})), "unit": "C", "parameter": "T2M", "evidence_type": "MODELED"},
            "precipitation_context": {"value": _first_value(parameters.get("PRECTOTCORR", {})), "unit": "mm/day", "parameter": "PRECTOTCORR", "evidence_type": "MODELED"},
            "solar_radiation": {"value": _first_value(parameters.get("ALLSKY_SFC_SW_DWN", {})), "unit": "MJ/m^2/day", "parameter": "ALLSKY_SFC_SW_DWN", "evidence_type": "MODELED"},
            "temporal_resolution": "daily",
            "semantic_note": "NASA POWER is regional/model-derived environmental data, not an exact on-site sensor reading.",
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    canonical_url=canonical_url,
                    authority="NASA POWER",
                    geographic_scope="regional modeled grid",
                    license="unknown",
                    attribution="NASA POWER",
                    content_hash=content_hash(payload),
                )
            ],
        )

    def _get_json(self, url: str) -> dict:
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "GAIA Local Alpha/0.1"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


SDA_POST_URL = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"


class USDASoilDataAccessAdapter:
    """SSURGO soil survey context from the USDA NRCS Soil Data Access service.

    Survey context only — map unit, dominant component, and top-horizon
    properties. This is never live soil moisture, and an unmatched point
    returns UNAVAILABLE rather than a guessed soil type.
    """

    provider_id = "usda-nrcs-sda"

    def __init__(self, *, base_url: str = SDA_POST_URL, user_agent: str = "GAIA Local Alpha/0.1", timeout_seconds: float = 20.0) -> None:
        self.base_url = base_url
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    async def soil_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        return await asyncio.to_thread(self._soil_context_sync, latitude, longitude)

    def _soil_context_sync(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        body = json.dumps({"SERVICE": "query", "FORMAT": "JSON+COLUMNNAME", "QUERY": self.build_query(latitude, longitude)}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": self.user_agent},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return self._unavailable(f"ssurgo_http_{exc.code}", {})
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return self._unavailable(f"ssurgo_error:{exc.__class__.__name__}", {})
        return self.normalize_mapunit_response(payload, self.base_url)

    def build_query(self, latitude: float, longitude: float) -> str:
        # ~11 m precision: far finer than any SSURGO map unit, so this costs no
        # accuracy while keeping full-precision coordinates off the wire.
        point = f"point({round(longitude, 4)} {round(latitude, 4)})"
        return (
            "SELECT TOP 1 mu.muname, c.compname, c.drainagecl, c.hydgrp, c.slope_l, c.slope_h, "
            "ch.texture, ch.ph1to1h2o_r, ch.awc_r, ch.om_r, cr.resdept_r "
            f"FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{point}') AS m "
            "INNER JOIN mapunit mu ON mu.mukey = m.mukey "
            "INNER JOIN component c ON c.mukey = mu.mukey AND c.majcompflag = 'Yes' "
            "LEFT OUTER JOIN chorizon ch ON ch.cokey = c.cokey AND ch.hzdept_r = 0 "
            "LEFT OUTER JOIN corestrictions cr ON cr.cokey = c.cokey "
            "ORDER BY c.comppct_r DESC"
        )

    def normalize_mapunit_response(self, payload: dict, canonical_url: str) -> EnvironmentalProviderResult:
        rows = _sda_rows(payload)
        if not rows:
            return self._unavailable("No soil survey result available; GAIA did not infer a soil type.", payload, canonical_url=canonical_url)
        row = rows[0]
        data = {
            "map_unit": row.get("muname"),
            "component": row.get("compname"),
            "drainage_class": row.get("drainagecl"),
            "hydrologic_soil_group": row.get("hydgrp"),
            "available_water_capacity": {"value": _sda_number(row.get("awc_r")), "evidence_type": "SURVEY"},
            "texture": {"value": row.get("texture"), "evidence_type": "SURVEY"},
            "organic_matter": {"value": _sda_number(row.get("om_r")), "evidence_type": "SURVEY"},
            "ph": {"value": _sda_number(row.get("ph1to1h2o_r")), "evidence_type": "SURVEY"},
            "slope": {"value": _slope_range(row), "evidence_type": "SURVEY"},
            "restrictive_depth": {"value": _sda_number(row.get("resdept_r")), "evidence_type": "SURVEY"},
            "semantic_note": "SSURGO is soil survey context, not live soil moisture.",
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=str(row.get("muname") or "ssurgo-mapunit"),
                    canonical_url=canonical_url,
                    authority="USDA NRCS Soil Data Access",
                    geographic_scope="soil survey map unit",
                    license="public domain (U.S. federal government work)",
                    attribution="USDA NRCS",
                    content_hash=content_hash(payload),
                )
            ],
        )

    def _unavailable(self, note: str, payload: dict, *, canonical_url: str | None = None) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(
            status="UNAVAILABLE",
            data={"semantic_note": note},
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    canonical_url=canonical_url or self.base_url,
                    authority="USDA NRCS Soil Data Access",
                    license="public domain (U.S. federal government work)",
                    attribution="USDA NRCS",
                    content_hash=content_hash(payload),
                )
            ],
        )


class USGSWaterApiAdapter:
    """Nearby hydrologic sites and current readings from USGS Water Services.

    Free and keyless. Streamflow and gage height are watershed context, never a
    field-level soil-moisture or irrigation measurement.
    """

    provider_id = "usgs-water"

    # 00060 discharge (cfs), 00065 gage height (ft), 00010 water temperature (C).
    DEFAULT_PARAMETERS = "00060,00065,00010"

    def __init__(
        self,
        *,
        base_url: str = "https://waterservices.usgs.gov/nwis",
        user_agent: str = "GAIA Local Alpha/0.1",
        search_radius_degrees: float = 0.25,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.search_radius_degrees = search_radius_degrees
        self.timeout_seconds = timeout_seconds

    async def nearby_sites(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        return await asyncio.to_thread(self._fetch, latitude, longitude, "sites")

    async def current_conditions(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        return await asyncio.to_thread(self._fetch, latitude, longitude, "current")

    async def historical_conditions(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        # Daily-values retrieval is a separate NWIS service; not wired yet, and
        # an empty success would read as "no water history exists".
        return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["usgs_historical_daily_values_not_implemented"])

    def _fetch(self, latitude: float, longitude: float, mode: str) -> EnvironmentalProviderResult:
        url = self.request_url(latitude, longitude)
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # NWIS answers 404 when the bounding box contains no active sites.
            if exc.code == 404:
                return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["usgs_no_sites_in_search_area"])
            return EnvironmentalProviderResult(status="PROVIDER_ERROR", warnings=[f"usgs_http_{exc.code}"])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return EnvironmentalProviderResult(status="PROVIDER_ERROR", warnings=[f"usgs_error:{exc.__class__.__name__}"])
        return self.normalize_instantaneous_response(payload, url, mode=mode)

    def request_url(self, latitude: float, longitude: float) -> str:
        # Coordinates become a bounding box rounded to ~1 km, so an exact
        # private location never reaches USGS.
        latitude = round(latitude, 2)
        longitude = round(longitude, 2)
        radius = self.search_radius_degrees
        bbox = f"{longitude - radius:.2f},{latitude - radius:.2f},{longitude + radius:.2f},{latitude + radius:.2f}"
        params = urllib.parse.urlencode(
            {"format": "json", "bBox": bbox, "parameterCd": self.DEFAULT_PARAMETERS, "siteStatus": "active"}
        )
        return f"{self.base_url}/iv/?{params}"

    def normalize_instantaneous_response(self, payload: dict, url: str | None = None, *, mode: str = "sites") -> EnvironmentalProviderResult:
        series = ((payload.get("value") or {}).get("timeSeries")) or []
        sites: dict[str, dict] = {}
        for entry in series:
            source_info = entry.get("sourceInfo") or {}
            site_code = _first_site_code(source_info)
            if not site_code:
                continue
            site = sites.setdefault(
                site_code,
                {"site_no": site_code, "name": source_info.get("siteName"), "measurements": {}},
            )
            reading = _latest_reading(entry)
            if reading is not None:
                variable = entry.get("variable") or {}
                name = str((variable.get("variableCode") or [{}])[0].get("value") or "unknown")
                site["measurements"][_PARAMETER_LABELS.get(name, name)] = reading
        ordered = [site for site in sites.values() if site["measurements"] or mode == "sites"]
        if not ordered:
            return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["usgs_no_sites_in_search_area"])
        data = {
            "sites": ordered,
            "evidence_type": "OBSERVED",
            "semantic_note": "USGS streamflow and gage readings are watershed context, not field soil moisture or irrigation guidance.",
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=ordered[0]["site_no"],
                    canonical_url=url or f"{self.base_url}/iv/",
                    authority="U.S. Geological Survey Water Services",
                    geographic_scope="nearby hydrologic sites",
                    license="public domain (U.S. federal government work)",
                    attribution="USGS",
                    content_hash=content_hash(payload),
                )
            ],
        )


_PARAMETER_LABELS = {
    "00060": "discharge_cfs",
    "00065": "gage_height_ft",
    "00010": "water_temperature_c",
}


def _first_site_code(source_info: dict) -> str | None:
    codes = source_info.get("siteCode") or []
    if not codes:
        return None
    value = codes[0].get("value")
    return str(value) if value else None


def _latest_reading(entry: dict) -> dict | None:
    values = entry.get("values") or []
    points = values[0].get("value") if values else None
    if not points:
        return None
    latest = points[-1]
    number = _sda_number(latest.get("value"))
    # NWIS encodes "no current reading" as -999999.
    if number is None or number <= -999999:
        return None
    unit = ((entry.get("variable") or {}).get("unit") or {}).get("unitCode")
    return {"value": number, "unit": unit, "observed_at": latest.get("dateTime"), "evidence_type": "OBSERVED"}


def _sda_rows(payload: dict) -> list[dict]:
    """Normalize SDA's Table shape into dicts.

    JSON+COLUMNNAME returns the column-name array as the first row; some
    callers already hold dict rows. Both are accepted.
    """
    table = payload.get("Table") or []
    if not table:
        return []
    if isinstance(table[0], dict):
        return [row for row in table if isinstance(row, dict)]
    columns = [str(name) for name in table[0]]
    return [dict(zip(columns, row)) for row in table[1:] if isinstance(row, list)]


def _sda_number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _slope_range(row: dict) -> str | None:
    low = _sda_number(row.get("slope_l"))
    high = _sda_number(row.get("slope_h"))
    if low is None and high is None:
        return None
    if low is not None and high is not None:
        return f"{low:g}-{high:g}%"
    return f"{(low if low is not None else high):g}%"


def _first_value(values: dict) -> float | None:
    if not values:
        return None
    return _normalize_power_value(next(iter(values.values())))


def _normalize_power_value(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            value = float(stripped)
        except ValueError:
            return None
    if value in NASA_POWER_MISSING_VALUES:
        return None
    return value


def _power_date(at_time: str | None) -> str:
    if at_time:
        normalized = at_time[:10].replace("-", "")
        if len(normalized) == 8 and normalized.isdigit():
            return normalized
    return (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y%m%d")
