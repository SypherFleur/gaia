from __future__ import annotations

from packages.mercator.normalization import classify_freshness, normalize_commodity, normalize_unit
from packages.mercator.providers import EconomicProviderResult, EconomicRequest
from packages.provenance import ProvenanceRecord, content_hash


class FixtureNASSProvider:
    provider_id = "usda-nass"

    def __init__(self, *, unavailable: bool = False, missing_county: bool = False) -> None:
        self.unavailable = unavailable
        self.missing_county = missing_county
        self.calls = 0
        self.last_request: EconomicRequest | None = None

    async def production(self, request: EconomicRequest) -> EconomicProviderResult:
        self.calls += 1
        self.last_request = request
        if self.unavailable:
            return EconomicProviderResult(status="PROVIDER_ERROR", warnings=["nass_fixture_unavailable"])
        commodity = normalize_commodity(request.commodity, crop_or_taxon=request.crop_or_taxon)
        geography = dict(request.geography)
        if self.missing_county:
            geography = {key: value for key, value in geography.items() if key not in {"county_or_district", "county_fips"}}
            geography["state_level_fallback"] = True
        stats = [
            {
                "statistic": "production",
                "commodity": commodity,
                "value": 12500,
                "unit": "cwt",
                "unit_context": normalize_unit(12500, "cwt"),
                "geography": geography,
                "observation_period": "2025",
                "publication_date": "2026-02-15",
                "data_class": "RECENT_PERIODIC_STATISTIC",
                "freshness": classify_freshness("RECENT_PERIODIC_STATISTIC", "2025", "2026-02-15"),
                "source_native_label": "TOMATOES, FRESH MARKET",
                "provider_record_id": "nass-fixture-tomato-production-2025",
                "limitations": ["Annual NASS statistic; not current crop availability."],
            },
            {
                "statistic": "yield",
                "commodity": commodity,
                "value": 240,
                "unit": "cwt / acre",
                "unit_context": normalize_unit(240, "cwt / acre"),
                "geography": geography,
                "observation_period": "2025",
                "publication_date": "2026-02-15",
                "data_class": "RECENT_PERIODIC_STATISTIC",
                "freshness": classify_freshness("RECENT_PERIODIC_STATISTIC", "2025", "2026-02-15"),
                "source_native_label": "YIELD, MEASURED IN CWT / ACRE",
                "provider_record_id": "nass-fixture-tomato-yield-2025",
                "limitations": ["Annual NASS statistic; period must remain attached."],
            },
        ]
        return EconomicProviderResult(
            status="AVAILABLE",
            data={"production_statistics": stats},
            provenance=[_prov(self.provider_id, "nass-fixture-tomato-production-2025", "https://quickstats.nass.usda.gov/api")],
            freshness="recent_periodic",
        )

    async def market_reports(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNSUPPORTED_LOCATION", warnings=["nass_market_reports_not_primary"])

    async def prices(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNSUPPORTED_LOCATION", warnings=["nass_prices_not_primary_for_phase10"])

    async def regional_context(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(
            status="AVAILABLE",
            data={
                "regional_economic_context": [
                    {
                        "metric": "agricultural_concentration",
                        "value": "limited fixture context",
                        "geography": request.geography,
                        "observation_period": "2022 Census of Agriculture",
                        "publication_date": "2024-02-13",
                        "data_class": "REGIONAL_ECONOMIC_CONTEXT",
                        "freshness": "regional_context",
                        "limitations": ["Explanatory county context; not crop profitability."],
                    }
                ]
            },
            provenance=[_prov(self.provider_id, "nass-fixture-region-2022", "https://www.nass.usda.gov/AgCensus/")],
            freshness="regional_context",
        )

    async def supply_chain(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNSUPPORTED_LOCATION", warnings=["nass_supply_chain_not_primary"])


class FixtureAMSProvider:
    provider_id = "usda-ams"

    def __init__(self, *, unavailable: bool = False, historical_report: bool = False) -> None:
        self.unavailable = unavailable
        self.historical_report = historical_report
        self.calls = 0
        self.last_request: EconomicRequest | None = None

    async def production(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNSUPPORTED_LOCATION", warnings=["ams_production_not_primary"])

    async def market_reports(self, request: EconomicRequest) -> EconomicProviderResult:
        self.calls += 1
        self.last_request = request
        if self.unavailable:
            return EconomicProviderResult(status="PROVIDER_ERROR", warnings=["ams_fixture_unavailable"])
        report_date = "2026-08-10" if not self.historical_report else "2024-08-10"
        commodity = normalize_commodity(request.commodity, crop_or_taxon=request.crop_or_taxon)
        observation = {
            "market": request.market_region or "Dallas terminal market fixture",
            "commodity": commodity,
            "report_date": report_date,
            "publication_date": report_date,
            "value": 18.0,
            "unit": "$/25 lb box",
            "unit_context": normalize_unit(18.0, "$/25 lb box", package="25 lb box", grade="medium"),
            "package": "25 lb box",
            "grade": "medium",
            "currency": "USD",
            "currency_date_context": report_date,
            "geography": request.geography,
            "data_class": "REALTIME_OR_CURRENT_REPORT",
            "freshness": classify_freshness("REALTIME_OR_CURRENT_REPORT", report_date, report_date),
            "source_report": "AMS MyMarketNews fixture produce terminal report",
            "provider_record_id": f"ams-fixture-tomato-{report_date}",
            "limitations": ["Market report observation; not a price forecast."],
        }
        return EconomicProviderResult(
            status="AVAILABLE",
            data={"market_reports": [observation], "price_observations": [observation]},
            provenance=[_prov(self.provider_id, f"ams-fixture-tomato-{report_date}", "https://mymarketnews.ams.usda.gov/mymarketnews-api")],
            freshness=observation["freshness"],
        )

    async def prices(self, request: EconomicRequest) -> EconomicProviderResult:
        return await self.market_reports(request)

    async def regional_context(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNSUPPORTED_LOCATION", warnings=["ams_region_not_primary"])

    async def supply_chain(self, request: EconomicRequest) -> EconomicProviderResult:
        commodity = normalize_commodity(request.commodity, crop_or_taxon=request.crop_or_taxon)
        record = {
            "commodity": commodity,
            "origin_region": {"label": "Texas fixture production region"},
            "destination_region": {"label": request.market_region or "Dallas terminal market fixture"},
            "transport_mode": "truck",
            "value": None,
            "weight": None,
            "period": "2022",
            "publication_date": "2024-01-01",
            "source": "Fixture structural movement dataset",
            "data_class": "STRUCTURAL_SUPPLY_CHAIN",
            "freshness": "structural_historical",
            "limitations": ["Historical structural context; not live logistics."],
        }
        return EconomicProviderResult(
            status="AVAILABLE",
            data={"supply_chain_context": [record]},
            provenance=[_prov(self.provider_id, "ams-fixture-structural-flow-2022", "https://mymarketnews.ams.usda.gov/")],
            freshness="structural_historical",
        )


def _prov(provider: str, record_id: str, url: str) -> ProvenanceRecord:
    return ProvenanceRecord(
        provider=provider,
        external_record_id=record_id,
        canonical_url=url,
        authority=provider,
        geographic_scope="US fixture",
        license="public domain / U.S. government source where applicable; fixture normalized for tests",
        attribution=provider,
        content_hash=content_hash({"provider": provider, "record_id": record_id}),
    )

