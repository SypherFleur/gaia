from __future__ import annotations

import asyncio
import unittest

from packages.mercator import FixtureAMSProvider, FixtureNASSProvider
from packages.mercator.live_adapters import AMSMyMarketNewsProvider, NASSQuickStatsProvider
from packages.mercator.providers import EconomicRequest


GEOGRAPHY = {"country_code": "US", "state_code": "TX", "county_or_district": "Travis County", "county_fips": "48453"}

NASS_PAYLOAD = {
    "data": [
        {
            "commodity_desc": "TOMATOES",
            "statisticcat_desc": "PRODUCTION",
            "short_desc": "TOMATOES, FRESH MARKET - PRODUCTION, MEASURED IN CWT",
            "unit_desc": "CWT",
            "Value": "12,500",
            "year": "2025",
            "state_alpha": "TX",
            "county_name": "TRAVIS",
            "agg_level_desc": "COUNTY",
            "load_time": "2026-02-15 00:00:00",
        },
        {
            "commodity_desc": "TOMATOES",
            "statisticcat_desc": "PRODUCTION",
            "unit_desc": "CWT",
            "Value": "(D)",
            "year": "2024",
            "state_alpha": "TX",
            "county_name": "TRAVIS",
            "agg_level_desc": "COUNTY",
            "load_time": "2025-02-15 00:00:00",
        },
    ]
}

AMS_PAYLOAD = {
    "results": [
        {
            "report_title": "National Fruit and Vegetable Terminal Market",
            "market_location_name": "DALLAS",
            "market_location_code": "DA",
            "report_date": "08/10/2026",
            "commodity": "TOMATOES",
            "package": "25 lb box",
            "grade": "medium",
            "avg_price": "18.00",
        },
        {
            "market_location_name": "DALLAS",
            "report_date": "08/10/2026",
            "package": "25 lb box",
            "avg_price": "(NA)",
        },
    ]
}


def run(coro):
    return asyncio.run(coro)


def request() -> EconomicRequest:
    return EconomicRequest(commodity="tomato", geography=GEOGRAPHY, periods=["2024"])


class NASSLiveNormalizationTest(unittest.TestCase):
    def test_live_production_matches_fixture_contract_shape(self) -> None:
        fixture = run(FixtureNASSProvider().production(request()))
        live = NASSQuickStatsProvider().normalize_production_response(request(), NASS_PAYLOAD, "https://quickstats.nass.usda.gov/api/api_GET/?key=REDACTED")

        self.assertEqual(live.status, "AVAILABLE")
        fixture_stat = fixture.data["production_statistics"][0]
        live_stat = live.data["production_statistics"][0]
        self.assertEqual(set(live_stat), set(fixture_stat))
        self.assertEqual(live_stat["commodity"]["canonical_name"], "tomato")
        self.assertEqual(live_stat["value"], 12500.0)
        self.assertEqual(live_stat["unit"], "CWT")
        self.assertEqual(live_stat["observation_period"], "2025")
        self.assertEqual(live_stat["publication_date"], "2026-02-15")
        self.assertEqual(live_stat["geography"]["county_or_district"], "Travis")
        self.assertEqual(live.provenance[0].provider, "usda-nass")

    def test_suppressed_values_are_dropped_not_guessed(self) -> None:
        live = NASSQuickStatsProvider().normalize_production_response(request(), NASS_PAYLOAD)

        # The "(D)" disclosure-suppressed row must not become a statistic.
        self.assertEqual(len(live.data["production_statistics"]), 1)

    def test_all_suppressed_response_is_unavailable(self) -> None:
        payload = {"data": [{"Value": "(D)", "year": "2025", "unit_desc": "CWT"}]}
        live = NASSQuickStatsProvider().normalize_production_response(request(), payload)

        self.assertEqual(live.status, "UNAVAILABLE")
        self.assertIn("nass_values_suppressed_or_non_numeric", live.warnings)

    def test_empty_response_is_unavailable_not_fabricated(self) -> None:
        live = NASSQuickStatsProvider().normalize_production_response(request(), {"data": []})

        self.assertEqual(live.status, "UNAVAILABLE")
        self.assertEqual(live.data, {})

    def test_state_level_answer_drops_county_claim(self) -> None:
        payload = {"data": [dict(NASS_PAYLOAD["data"][0], county_name="", agg_level_desc="STATE")]}
        live = NASSQuickStatsProvider().normalize_production_response(request(), payload)
        geography = live.data["production_statistics"][0]["geography"]

        self.assertNotIn("county_or_district", geography)
        self.assertTrue(geography["state_level_fallback"])

    def test_request_url_redacts_api_key_for_provenance(self) -> None:
        provider = NASSQuickStatsProvider()
        url = provider.request_url(request(), "secret-key-value")
        self.assertIn("secret-key-value", url)

        from packages.mercator.live_adapters import _redact_key

        self.assertNotIn("secret-key-value", _redact_key(url))
        self.assertIn("key=REDACTED", _redact_key(url))

    def test_missing_key_fails_closed(self) -> None:
        provider = NASSQuickStatsProvider(api_key_env="GAIA_NASS_KEY_ABSENT_FOR_TEST")
        result = run(provider.production(request()))

        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertIn("nass_api_key_not_configured", result.warnings)


class AMSLiveNormalizationTest(unittest.TestCase):
    def test_live_market_report_matches_fixture_contract_shape(self) -> None:
        fixture = run(FixtureAMSProvider().market_reports(request()))
        live = AMSMyMarketNewsProvider().normalize_market_response(request(), AMS_PAYLOAD, "https://marsapi.ams.usda.gov/services/v1.2/reports/2651")

        self.assertEqual(live.status, "AVAILABLE")
        fixture_observation = fixture.data["market_reports"][0]
        live_observation = live.data["market_reports"][0]
        self.assertEqual(set(live_observation), set(fixture_observation))
        self.assertEqual(live_observation["value"], 18.0)
        self.assertEqual(live_observation["package"], "25 lb box")
        self.assertEqual(live_observation["grade"], "medium")
        self.assertEqual(live_observation["report_date"], "2026-08-10")
        self.assertEqual(live.data["price_observations"], live.data["market_reports"])
        self.assertEqual(live.provenance[0].provider, "usda-ams")

    def test_non_numeric_prices_are_dropped(self) -> None:
        live = AMSMyMarketNewsProvider().normalize_market_response(request(), AMS_PAYLOAD)
        self.assertEqual(len(live.data["market_reports"]), 1)

    def test_empty_report_is_unavailable(self) -> None:
        live = AMSMyMarketNewsProvider().normalize_market_response(request(), {"results": []})

        self.assertEqual(live.status, "UNAVAILABLE")
        self.assertIn("ams_report_matched_no_observations", live.warnings)

    def test_missing_key_fails_closed(self) -> None:
        provider = AMSMyMarketNewsProvider(api_key_env="GAIA_AMS_KEY_ABSENT_FOR_TEST")
        result = run(provider.market_reports(request()))

        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertIn("ams_api_key_not_configured", result.warnings)

    def test_unreachable_endpoint_fails_closed(self) -> None:
        import os

        os.environ["GAIA_AMS_KEY_FOR_FAILURE_TEST"] = "test-key"
        try:
            provider = AMSMyMarketNewsProvider(
                api_key_env="GAIA_AMS_KEY_FOR_FAILURE_TEST",
                base_url="http://127.0.0.1:9",
                timeout_seconds=0.2,
            )
            result = run(provider.market_reports(request()))

            self.assertEqual(result.status, "PROVIDER_ERROR")
            self.assertTrue(any(warning.startswith("ams_") for warning in result.warnings))
        finally:
            os.environ.pop("GAIA_AMS_KEY_FOR_FAILURE_TEST", None)


if __name__ == "__main__":
    unittest.main()
