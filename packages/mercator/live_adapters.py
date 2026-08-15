from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from packages.mercator.providers import EconomicProviderResult, EconomicRequest


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


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
        params = {
            "key": api_key,
            "format": "JSON",
            "commodity_desc": request.commodity.upper(),
            "year__GE": request.periods[0] if request.periods else "2020",
        }
        state = request.geography.get("state_code")
        if state:
            params["state_alpha"] = str(state)
        url = "https://quickstats.nass.usda.gov/api/api_GET/?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return EconomicProviderResult(status="AVAILABLE", data={"raw_record_count": len(payload.get("data", []))}, warnings=["live_normalization_deferred_to_fixture_contracts"])

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

    def __init__(self, *, api_key_env: str = "GAIA_AMS_API_KEY", timeout_seconds: float = 10.0) -> None:
        super().__init__()
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds

    async def market_reports(self, request: EconomicRequest) -> EconomicProviderResult:
        api_key = _first_env(self.api_key_env, "USDA_AMS_API_KEY")
        if not api_key:
            return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_api_key_not_configured"])
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_live_endpoint_requires_explicit_report_selection"])

    async def production(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_production_not_supported"])

    async def prices(self, request: EconomicRequest) -> EconomicProviderResult:
        return await self.market_reports(request)

    async def regional_context(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_regional_context_not_supported"])

    async def supply_chain(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_live_supply_chain_normalization_deferred"])
