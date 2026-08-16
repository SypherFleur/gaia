from __future__ import annotations

import asyncio
import json
import os
import unittest
import urllib.error

from packages.botany.live_adapters import GBIFApiAdapter
from packages.botany.providers import TaxonomyResolution
from packages.environment.live_adapters import USDASoilDataAccessAdapter
from packages.providers.verification import (
    PROBE_LATITUDE,
    PROBE_LONGITUDE,
    ProbeResult,
    _outcome_for,
    probe_coordinate,
    summarize,
    verify_live_providers,
)


def run(coro):
    return asyncio.run(coro)


SDA_COLUMNS = ["muname", "compname", "drainagecl", "hydgrp", "slope_l", "slope_h", "texdesc", "ph1to1h2o_r", "awc_r", "om_r", "resdept_r"]
SDA_ROW = ["Austin silty clay, 1 to 3 percent slopes", "Austin", "well drained", "D", "1.0", "3.0", "silty clay", "7.8", "0.17", "2.5", None]

GBIF_MATCH = {
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
}


class SSURGORequestContractTest(unittest.TestCase):
    """The live SSURGO request returned HTTP 400. Both causes are covered here."""

    def setUp(self) -> None:
        self.adapter = USDASoilDataAccessAdapter()

    def test_request_body_uses_the_lowercase_post_rest_contract(self) -> None:
        body = self.adapter.request_body(PROBE_LATITUDE, PROBE_LONGITUDE)

        self.assertEqual(set(body), {"query", "format"})
        self.assertEqual(body["format"], "JSON+COLUMNNAME")
        # Uppercase keys and a SERVICE key belong to the older
        # SDMTabularService endpoint and are rejected with HTTP 400.
        self.assertNotIn("SERVICE", body)
        self.assertNotIn("QUERY", body)
        self.assertNotIn("FORMAT", body)
        self.assertTrue(json.dumps(body))

    def test_query_does_not_select_a_nonexistent_chorizon_column(self) -> None:
        query = self.adapter.build_query(PROBE_LATITUDE, PROBE_LONGITUDE)

        # chorizon has no `texture` column; selecting it is an invalid-column
        # error, which SDA answers with HTTP 400.
        self.assertNotIn("ch.texture", query)
        self.assertIn("ctg.texdesc", query)
        self.assertIn("chtexturegrp", query)

    def test_query_uses_uppercase_wkt_at_the_probe_coordinate(self) -> None:
        query = self.adapter.build_query(PROBE_LATITUDE, PROBE_LONGITUDE)

        self.assertIn(f"POINT({PROBE_LONGITUDE} {PROBE_LATITUDE})", query)
        self.assertNotIn("point(", query)

    def test_probe_coordinate_query_is_well_formed(self) -> None:
        query = self.adapter.build_query(PROBE_LATITUDE, PROBE_LONGITUDE)

        self.assertIn("SDA_Get_Mukey_from_intersection_with_WktWgs84", query)
        self.assertIn("INNER JOIN mapunit mu ON mu.mukey = m.mukey", query)
        self.assertEqual(query.count("SELECT"), 1)
        self.assertNotIn(";", query)


class SSURGOOutcomeTest(unittest.TestCase):
    def test_valid_response_at_probe_coordinate_is_ok(self) -> None:
        payload = {"Table": [SDA_COLUMNS, SDA_ROW]}
        result = USDASoilDataAccessAdapter().normalize_mapunit_response(payload, "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest")

        self.assertEqual(result.status, "AVAILABLE")
        self.assertEqual(result.data["texture"]["value"], "silty clay")
        self.assertEqual(result.data["component"], "Austin")
        outcome, detail, sample = _outcome_for(result, {"map_unit": result.data["map_unit"]})
        self.assertEqual(outcome, "OK")
        self.assertEqual(detail, "")
        self.assertTrue(sample["map_unit"])

    def test_legacy_texture_key_still_normalizes(self) -> None:
        columns = [name if name != "texdesc" else "texture" for name in SDA_COLUMNS]
        result = USDASoilDataAccessAdapter().normalize_mapunit_response({"Table": [columns, SDA_ROW]}, "https://example.invalid")

        self.assertEqual(result.data["texture"]["value"], "silty clay")

    def test_genuine_no_coverage_is_no_data_not_failed(self) -> None:
        result = USDASoilDataAccessAdapter().normalize_mapunit_response({"Table": []}, "https://example.invalid")
        outcome, detail, _ = _outcome_for(result, {})

        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(outcome, "NO_DATA")
        self.assertIn("did not infer", detail)

    def test_http_400_remains_a_failure(self) -> None:
        result = USDASoilDataAccessAdapter()._unavailable("ssurgo_http_400: invalid column", {})
        outcome, detail, _ = _outcome_for(result, {})

        self.assertEqual(outcome, "FAILED")
        self.assertIn("400", detail)


class GBIFOutcomeTest(unittest.TestCase):
    """GBIF answered correctly; the verifier misread its status vocabulary."""

    def test_accepted_taxonomy_is_ok_not_failed(self) -> None:
        resolution = GBIFApiAdapter(user_agent="test").normalize_match_response("tomato", GBIF_MATCH)
        outcome, detail, sample = _outcome_for(resolution, {"accepted_name": resolution.accepted_scientific_name})

        # Taxonomy reports ACCEPTED, never AVAILABLE — a resolved match is a
        # success, not a missing status.
        self.assertEqual(resolution.status, "ACCEPTED")
        self.assertEqual(outcome, "OK")
        self.assertEqual(detail, "")
        self.assertEqual(sample["accepted_name"], "Solanum lycopersicum")

    def test_semantic_caveat_survives_as_a_warning_not_a_failure(self) -> None:
        resolution = GBIFApiAdapter(user_agent="test").normalize_match_response("tomato", GBIF_MATCH)
        probe = ProbeResult("gbif", "Taxonomy (GBIF)", "OK", "", [str(item) for item in resolution.warnings])

        self.assertIn("occurrence_is_not_cultivation_suitability", probe.warnings)
        self.assertEqual(probe.outcome, "OK")
        self.assertEqual(probe.detail, "")
        # The domain rule must stay visible: occurrence is not native range,
        # cultivation suitability, or legal availability.
        self.assertIn("occurrence_is_not_cultivation_suitability", probe.to_dict()["warnings"])

    def test_synonym_and_ambiguous_matches_are_also_ok(self) -> None:
        synonym = GBIFApiAdapter(user_agent="test").normalize_match_response("Lycopersicon esculentum", dict(GBIF_MATCH, synonym=True))
        ambiguous = GBIFApiAdapter(user_agent="test").normalize_match_response("pepper", dict(GBIF_MATCH, alternatives=[{"scientificName": "Capsicum annuum"}]))

        self.assertEqual(_outcome_for(synonym, {})[0], "OK")
        self.assertEqual(_outcome_for(ambiguous, {})[0], "OK")

    def test_unresolved_name_is_no_data(self) -> None:
        resolution = GBIFApiAdapter(user_agent="test").normalize_match_response("zzzz", {"matchType": "NONE"})
        outcome, _, _ = _outcome_for(resolution, {})

        self.assertEqual(outcome, "NO_DATA")

    def test_network_failure_is_failed(self) -> None:
        adapter = GBIFApiAdapter(user_agent="test", base_url="http://127.0.0.1:9", timeout_seconds=0.2)
        resolution = run(adapter.resolve_taxon("tomato"))
        outcome, detail, _ = _outcome_for(resolution, {})

        self.assertEqual(resolution.status, "PROVIDER_ERROR")
        self.assertEqual(outcome, "FAILED")
        self.assertIn("gbif_error", detail)

    def test_http_error_is_failed(self) -> None:
        resolution = TaxonomyResolution(status="PROVIDER_ERROR", query="tomato", warnings=["gbif_http_503"])
        outcome, detail, _ = _outcome_for(resolution, {})

        self.assertEqual(outcome, "FAILED")
        self.assertIn("503", detail)

    def test_unusable_schema_is_failed(self) -> None:
        # A drifted payload with no usable identity must not read as success.
        resolution = TaxonomyResolution(status="PROVIDER_ERROR", query="tomato", warnings=["gbif_schema_unusable"])
        self.assertEqual(_outcome_for(resolution, {})[0], "FAILED")


class ProbeCoordinateLabellingTest(unittest.TestCase):
    def test_probe_coordinate_is_labelled_diagnostic_only(self) -> None:
        described = probe_coordinate(PROBE_LATITUDE, PROBE_LONGITUDE)

        self.assertEqual(described["purpose"], "provider_health_check")
        self.assertFalse(described["is_user_location"])
        self.assertIn("Not device location", described["note"])
        self.assertEqual(described["latitude"], PROBE_LATITUDE)

    def test_summary_carries_the_labelled_coordinate(self) -> None:
        summary = summarize([ProbeResult("a", "A", "OK")], latitude=1.5, longitude=-2.5)

        self.assertEqual(summary["probe_coordinate"]["latitude"], 1.5)
        self.assertEqual(summary["probe_coordinate"]["longitude"], -2.5)
        self.assertFalse(summary["probe_coordinate"]["is_user_location"])

    def test_summary_exposes_warnings_separately_from_detail(self) -> None:
        results = [ProbeResult("gbif", "Taxonomy (GBIF)", "OK", "", ["occurrence_is_not_cultivation_suitability"])]
        summary = summarize(results)

        row = summary["providers"][0]
        self.assertEqual(row["outcome"], "OK")
        self.assertEqual(row["detail"], "")
        self.assertEqual(row["warnings"], ["occurrence_is_not_cultivation_suitability"])
        self.assertEqual(summary["failed"], 0)


@unittest.skipUnless(os.environ.get("GAIA_RUN_LIVE_PROVIDER_SMOKE") == "1", "Set GAIA_RUN_LIVE_PROVIDER_SMOKE=1 to probe real endpoints.")
class LiveProviderSmokeTest(unittest.TestCase):
    def test_no_provider_reports_a_transport_or_schema_failure(self) -> None:
        results = run(verify_live_providers())
        summary = summarize(results)
        failures = [row for row in summary["providers"] if row["outcome"] in {"FAILED", "ERROR"}]

        self.assertEqual(failures, [], f"live providers failed: {failures}")


if __name__ == "__main__":
    unittest.main()
