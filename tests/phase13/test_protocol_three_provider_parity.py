from __future__ import annotations

import asyncio
import unittest
from dataclasses import asdict

from packages.botany import FixtureGBIFProvider, FixtureGenesysProvider, GBIFApiAdapter, GenesysPGRAdapter, KewPOWOApiAdapter
from packages.environment.fixture_adapters import FixtureNASAPowerProvider, FixtureNWSProvider
from packages.environment.live_adapters import NASAPowerApiAdapter, NWSApiAdapter
from packages.research import EuropePMCAdapter, FixtureResearchProvider, normalize_europe_pmc_work
from packages.research.providers import ResearchSearchRequest
from packages.sentinel import (
    APHIS_CITRUS_URL,
    FDACS_IMPORT_REGULATIONS_URL,
    FixtureAPHISProvider,
    FixtureFloridaFDACSProvider,
    ReadOnlyRegulatoryPageAdapter,
    RegulationRequest,
)


class ProtocolThreeProviderParityTest(unittest.TestCase):
    def test_nws_live_normalizer_matches_fixture_environment_contract(self) -> None:
        fixture = run(FixtureNWSProvider().forecast(30.2672, -97.7431))
        live = NWSApiAdapter(user_agent="GAIA parity test").normalize_forecast(
            {
                "properties": {
                    "generatedAt": "2026-08-14T12:00:00Z",
                    "periods": [
                        {
                            "temperature": 65,
                            "temperatureUnit": "F",
                            "probabilityOfPrecipitation": {"value": 20},
                            "relativeHumidity": {"value": 71},
                            "windSpeed": "8 mph",
                            "windDirection": "SE",
                            "startTime": "2026-08-14T21:00:00-05:00",
                        }
                    ],
                }
            },
            "https://api.weather.gov/gridpoints/EWX/155,90/forecast",
        )

        self.assertEqual(set(asdict(live)), set(asdict(fixture)))
        self.assertEqual(set(live.data), set(fixture.data))
        self.assertEqual(set(asdict(live.provenance[0])), set(asdict(fixture.provenance[0])))

    def test_nasa_power_live_normalizer_matches_fixture_environment_contract(self) -> None:
        fixture = run(FixtureNASAPowerProvider().climate_context(30.2672, -97.7431))
        live = NASAPowerApiAdapter().normalize_daily_response(
            {
                "properties": {
                    "parameter": {
                        "T2M": {"20260814": 29.1},
                        "PRECTOTCORR": {"20260814": 2.1},
                        "ALLSKY_SFC_SW_DWN": {"20260814": 23.4},
                    }
                }
            },
            "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M",
        )

        self.assertEqual(set(asdict(live)), set(asdict(fixture)))
        self.assertEqual(set(live.data), set(fixture.data))
        self.assertEqual(set(asdict(live.provenance[0])), set(asdict(fixture.provenance[0])))

    def test_nasa_power_fill_values_normalize_to_missing(self) -> None:
        live = NASAPowerApiAdapter().normalize_daily_response(
            {
                "properties": {
                    "parameter": {
                        "T2M": {"20260814": 35.5},
                        "PRECTOTCORR": {"20260814": -999},
                        "ALLSKY_SFC_SW_DWN": {"20260814": "-999.0"},
                    }
                }
            },
            "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M",
        )

        self.assertEqual(live.data["temperature_history"]["value"], 35.5)
        self.assertIsNone(live.data["precipitation_context"]["value"])
        self.assertIsNone(live.data["solar_radiation"]["value"])

    def test_nasa_power_live_climate_context_uses_normalized_contract(self) -> None:
        adapter = StubNASAPowerAdapter()
        result = run(adapter.climate_context(30.2672, -97.7431, "2026-08-14T00:00:00Z"))

        self.assertEqual(result.status, "AVAILABLE")
        self.assertIn("start=20260814", adapter.last_url)
        self.assertIn("temperature_history", result.data)
        self.assertIn("semantic_note", result.data)

    def test_gbif_live_normalizer_matches_fixture_taxonomy_contract(self) -> None:
        fixture = run(FixtureGBIFProvider().resolve_taxon("tomato"))
        live = GBIFApiAdapter(user_agent="GAIA parity test").normalize_match_response(
            "tomato",
            {
                "usageKey": 2930137,
                "acceptedUsageKey": 2930137,
                "scientificName": "Solanum lycopersicum L.",
                "acceptedScientificName": "Solanum lycopersicum",
                "canonicalName": "Solanum lycopersicum",
                "matchType": "EXACT",
                "rank": "SPECIES",
                "status": "ACCEPTED",
                "kingdom": "Plantae",
                "family": "Solanaceae",
                "genus": "Solanum",
                "species": "Solanum lycopersicum",
            },
            "https://api.gbif.org/v1/species/match?name=tomato",
        )

        self.assertEqual(set(asdict(live)), set(asdict(fixture)))
        self.assertEqual(set(asdict(live.provenance[0])), set(asdict(fixture.provenance[0])))

    def test_genesys_live_adapter_fails_closed_instead_of_crashing(self) -> None:
        adapter = GenesysPGRAdapter(base_url="http://127.0.0.1:9", timeout_seconds=0.2)
        result = run(adapter.search_accessions("cowpea", limit=5))

        self.assertEqual(result.status, "PROVIDER_ERROR")
        self.assertTrue(any(warning.startswith("genesys_") for warning in result.warnings))

    def test_genesys_live_normalizer_matches_fixture_germplasm_contract(self) -> None:
        fixture = run(FixtureGenesysProvider().search_accessions("cowpea"))
        live = GenesysPGRAdapter().normalize_accession_search(
            "cowpea",
            {
                "content": [
                    {
                        "uuid": "acc-1",
                        "accessionNumber": "TVu-12345",
                        "taxonomy": {"genus": "Vigna", "species": "unguiculata"},
                        "cropName": "cowpea",
                        "instituteCode": "NGA039",
                        "institute": {"code": "NGA039", "fullName": "IITA Genetic Resources Center"},
                        "origCty": "NGA",
                    }
                ]
            },
        )

        self.assertEqual(set(asdict(live)), set(asdict(fixture)))
        self.assertEqual(set(live.accessions[0]), set(fixture.accessions[0]))
        self.assertEqual(set(asdict(live.provenance[0])), set(asdict(fixture.provenance[0])))
        self.assertFalse(live.accessions[0]["availability_verified"])
        self.assertFalse(live.accessions[0]["legal_movement_verified"])

    def test_kew_powo_normalizer_preserves_rights_and_provider_boundary(self) -> None:
        live = KewPOWOApiAdapter(user_agent="GAIA parity test").normalize_search_response(
            "Solanum lycopersicum",
            {
                "results": [
                    {
                        "fqId": "urn:lsid:ipni.org:names:316947-2",
                        "name": "Solanum lycopersicum L.",
                        "rank": "Species",
                        "family": {"name": "Solanaceae"},
                        "genus": {"name": "Solanum"},
                        "commonNames": ["tomato"],
                    }
                ]
            },
            "https://powo.science.kew.org/api/2/search?q=Solanum%20lycopersicum",
        )

        self.assertEqual(live.status, "ACCEPTED")
        self.assertEqual(live.provenance[0].provider, "kew-powo")
        self.assertIn("Kew", live.provenance[0].authority)
        self.assertIn("kew_attribution_required", live.warnings)

    def test_europe_pmc_live_normalizer_matches_fixture_research_work_contract(self) -> None:
        fixture_response = run(FixtureResearchProvider().search(ResearchSearchRequest("calcium tomato", limit=1)))
        live = normalize_europe_pmc_work(
            {
                "id": "MED/10000001",
                "title": "Blossom-end rot of tomato: calcium transport, water stress, and management",
                "abstractText": "A review finds blossom-end rot is linked to calcium transport and water stress.",
                "pubYear": "2019",
                "journalTitle": "Horticultural Reviews",
                "doi": "10.1000/ber-review",
                "pmid": "10000001",
                "pubTypeList": {"pubType": ["Review"]},
                "isOpenAccess": "N",
                "authorString": "Doe J",
            }
        )

        self.assertEqual(set(asdict(live)), set(asdict(fixture_response.works[0])))
        self.assertEqual(EuropePMCAdapter().provider_id, fixture_response.provider_id)

    def test_aphis_live_read_only_adapter_matches_regulation_response_contract(self) -> None:
        request = RegulationRequest(
            jurisdiction_pack="us_federal",
            origin={"country_code": "US"},
            destination={"country_code": "US"},
            species="Citrus sinensis",
            plant_part="live plant",
            live_plant=True,
        )
        fixture = run(FixtureAPHISProvider().movement_rules(request))
        live = run(
            StubRegulatoryPageAdapter(
                provider_id="aphis",
                authority="USDA APHIS",
                urls=(APHIS_CITRUS_URL,),
            ).movement_rules(request)
        )

        self.assertEqual(set(asdict(live)), set(asdict(fixture)))
        self.assertEqual(set(asdict(live.provenance[0])), set(asdict(fixture.provenance[0])))
        self.assertEqual(live.rules, [])

    def test_fdacs_live_read_only_adapter_matches_regulation_response_contract(self) -> None:
        request = RegulationRequest(
            jurisdiction_pack="us_fl",
            origin={"state_code": "TX"},
            destination={"state_code": "FL"},
            species="Citrus sinensis",
            plant_part="live plant",
            live_plant=True,
        )
        fixture = run(FixtureFloridaFDACSProvider().movement_rules(request))
        live = run(
            StubRegulatoryPageAdapter(
                provider_id="florida-fdacs",
                authority="Florida Department of Agriculture and Consumer Services",
                urls=(FDACS_IMPORT_REGULATIONS_URL,),
            ).movement_rules(request)
        )

        self.assertEqual(set(asdict(live)), set(asdict(fixture)))
        self.assertEqual(set(asdict(live.provenance[0])), set(asdict(fixture.provenance[0])))
        self.assertEqual(live.rules, [])


class StubNASAPowerAdapter(NASAPowerApiAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.last_url = ""

    def _get_json(self, url: str) -> dict:
        self.last_url = url
        return {
            "properties": {
                "parameter": {
                    "T2M": {"20260814": 29.1},
                    "PRECTOTCORR": {"20260814": 2.1},
                    "ALLSKY_SFC_SW_DWN": {"20260814": 23.4},
                }
            }
        }


class StubRegulatoryPageAdapter(ReadOnlyRegulatoryPageAdapter):
    def _fetch(self, url: str) -> str:
        return f"<html><title>{self.authority}</title><body>{url}</body></html>"


def run(coro):
    return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main()
