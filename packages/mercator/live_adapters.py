from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from packages.mercator.fixture_adapters import FixtureAMSProvider, FixtureNASSProvider
from packages.mercator.providers import EconomicProviderResult, EconomicRequest


class NASSQuickStatsProvider(FixtureNASSProvider):
    provider_id = "usda-nass"

    def __init__(self, *, api_key_env: str = "GAIA_NASS_API_KEY", timeout_seconds: float = 10.0) -> None:
        super().__init__()
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds

    async def production(self, request: EconomicRequest) -> EconomicProviderResult:
        api_key = os.environ.get(self.api_key_env)
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


class AMSMyMarketNewsProvider(FixtureAMSProvider):
    provider_id = "usda-ams"

    def __init__(self, *, api_key_env: str = "GAIA_AMS_API_KEY", timeout_seconds: float = 10.0) -> None:
        super().__init__()
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds

    async def market_reports(self, request: EconomicRequest) -> EconomicProviderResult:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_api_key_not_configured"])
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["ams_live_endpoint_requires_explicit_report_selection"])

