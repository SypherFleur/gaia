from __future__ import annotations

import unittest

from packages.environment.providers import EnvironmentalProviderResult
from packages.geospatial.providers import AdminResolution, ProviderStatus
from packages.providers.verification import ProbeResult, _outcome_for, summarize


class OutcomeClassificationTest(unittest.TestCase):
    def test_available_is_ok_and_keeps_evidence(self) -> None:
        result = AdminResolution(status=ProviderStatus("AVAILABLE"), county_or_district="Travis County")
        outcome, detail, sample = _outcome_for(result, {"county": "Travis County"})

        self.assertEqual(outcome, "OK")
        self.assertEqual(detail, "")
        self.assertEqual(sample, {"county": "Travis County"})

    def test_genuine_no_coverage_is_no_data(self) -> None:
        result = AdminResolution(status=ProviderStatus("UNRESOLVED", "coordinate_outside_census_coverage"))
        outcome, detail, _ = _outcome_for(result, {})

        self.assertEqual(outcome, "NO_DATA")
        self.assertIn("coverage", detail)

    def test_transport_failure_is_not_reported_as_no_data(self) -> None:
        # An unreachable endpoint must never look like normal fail-closed
        # behavior; telling those apart is the whole point of this command.
        result = AdminResolution(status=ProviderStatus("UNAVAILABLE", "census_error:URLError"))
        outcome, detail, _ = _outcome_for(result, {})

        self.assertEqual(outcome, "FAILED")
        self.assertIn("URLError", detail)

    def test_http_status_failure_is_failed(self) -> None:
        result = AdminResolution(status=ProviderStatus("UNAVAILABLE", "census_http_503"))
        outcome, _, _ = _outcome_for(result, {})

        self.assertEqual(outcome, "FAILED")

    def test_reason_is_read_from_warnings_when_status_has_none(self) -> None:
        result = EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["usgs_no_sites_in_search_area"])
        outcome, detail, _ = _outcome_for(result, {})

        self.assertEqual(outcome, "NO_DATA")
        self.assertIn("no_sites", detail)

    def test_reason_is_read_from_semantic_note_when_warnings_are_empty(self) -> None:
        # SSURGO reports its explanation in the payload rather than warnings;
        # without this the outcome would be classified from an empty reason.
        result = EnvironmentalProviderResult(status="UNAVAILABLE", data={"semantic_note": "ssurgo_error:URLError"})
        outcome, detail, _ = _outcome_for(result, {})

        self.assertEqual(outcome, "FAILED")
        self.assertIn("ssurgo_error", detail)

    def test_provider_error_status_is_failed(self) -> None:
        result = EnvironmentalProviderResult(status="PROVIDER_ERROR", warnings=["nws_error:URLError"])
        outcome, _, _ = _outcome_for(result, {})

        self.assertEqual(outcome, "FAILED")


class SummaryTest(unittest.TestCase):
    def test_counts_group_errors_with_failures(self) -> None:
        results = [
            ProbeResult("a", "A", "OK"),
            ProbeResult("b", "B", "NO_DATA", "outside coverage"),
            ProbeResult("c", "C", "FAILED", "http_503"),
            ProbeResult("d", "D", "ERROR", "URLError"),
        ]

        summary = summarize(results)

        self.assertEqual(summary["checked"], 4)
        self.assertEqual(summary["ok"], 1)
        self.assertEqual(summary["no_data"], 1)
        self.assertEqual(summary["failed"], 2)
        self.assertEqual(len(summary["providers"]), 4)
        self.assertIn("fail-closed", summary["note"])


if __name__ == "__main__":
    unittest.main()
