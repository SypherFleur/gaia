from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from apps.cli.gaia import main


def invoke(*args: str) -> tuple[int, dict]:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = main(["--database", "sqlite:///:memory:", *args])
    return code, json.loads(stream.getvalue())


class GaiaCLITest(unittest.TestCase):
    def test_doctor_reports_zero_spend_and_sovereign_posture(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = main(["--database", "sqlite:///:memory:", "--sovereign", "doctor"])
        payload = json.loads(stream.getvalue())

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertFalse(payload["paid_providers_enabled"])
        self.assertFalse(payload["automatic_paid_usage_enabled"])
        self.assertFalse(payload["automatic_overage_enabled"])
        self.assertFalse(payload["private_egress_enabled"])

    def test_cost_status_preserves_twenty_dollar_reserve(self) -> None:
        code, payload = invoke("cost", "status")

        self.assertEqual(code, 0)
        self.assertEqual(payload["configured_reserve"], 20.0)
        self.assertEqual(payload["total_development_cash_spent"], 0.0)
        self.assertFalse(payload["paid_providers_enabled"])

    def test_providers_list_has_no_enabled_manual_paid_provider(self) -> None:
        code, payload = invoke("providers", "list")

        self.assertEqual(code, 0)
        self.assertTrue(payload["providers"])
        self.assertFalse(any(provider["enabled"] and provider["billing_class"] == "MANUAL_PAID" for provider in payload["providers"]))
        self.assertTrue(all("mode" in provider for provider in payload["providers"]))

    def test_architecture_command_reports_guidance_graph(self) -> None:
        code, payload = invoke("architecture")

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertIn(payload["orchestration"]["graph"]["engine"], {"langgraph", "langgraph-compatible-local"})
        self.assertTrue(payload["orchestration"]["legacy_custom_orchestrator_preserved"])

    def test_architecture_command_shows_clean_normal_location_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stream = io.StringIO()
            database = f"sqlite:///{Path(directory) / 'gaia-clean.sqlite3'}"
            with contextlib.redirect_stdout(stream):
                code = main(["--database", database, "architecture"])
            payload = json.loads(stream.getvalue())

        self.assertEqual(code, 0)
        self.assertIsNone(payload["location"]["active_location"])
        self.assertEqual(payload["location"]["locations"], [])

    def test_sources_list_reports_kew_and_cash_status(self) -> None:
        code, payload = invoke("sources", "list")

        self.assertEqual(code, 0)
        rows = {row["provider_id"]: row for row in payload["rows"]}
        self.assertEqual(rows["kew-powo"]["source_state"], "documented-only")
        self.assertEqual(payload["cash_status"]["total_development_cash_spent"], 0.0)

    def test_eval_run_counts_smoke_prompts(self) -> None:
        code, payload = invoke("eval", "run")

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertGreaterEqual(payload["prompt_count"], 79)

    def test_cli_sentinel_movement_uses_gateway_and_florida_pack(self) -> None:
        code, payload = invoke(
            "sentinel",
            "check-movement",
            "--origin",
            "tx-houston",
            "--destination",
            "fl-orlando",
            "--species",
            "Citrus sinensis",
            "--plant-part",
            "live plant",
            "--live-plant",
        )

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "RESTRICTED")
        self.assertTrue(any(rule["jurisdiction_pack"] == "us_fl" for rule in payload["applicable_rules"]))
        self.assertTrue(payload["source_record_ids"])

    def test_cli_non_us_legal_jurisdiction_fails_closed(self) -> None:
        code, payload = invoke(
            "sentinel",
            "check-movement",
            "--source-country",
            "SG",
            "--destination-country",
            "GH",
            "--species",
            "Vigna unguiculata",
            "--plant-part",
            "seed",
        )

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "UNRESOLVED")
        self.assertIn("non_us_jurisdiction_not_implemented", payload["unresolved_questions"])

    def test_cli_botanist_taxon_returns_global_profile_without_model_run(self) -> None:
        code, payload = invoke("botanist", "taxon", "--query", "cowpea")

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ACCEPTED")
        self.assertEqual(payload["plant_entity"]["scientific_name"], "Vigna unguiculata")
        self.assertIn("tropical savanna agriculture", payload["plant_profile"]["biomes"])
        self.assertTrue(payload["source_record_ids"])

    def test_cli_botanist_germplasm_preserves_genesys_caveat(self) -> None:
        code, payload = invoke("botanist", "germplasm", "--query", "heat tolerant cowpea", "--limit", "1")

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "AVAILABLE")
        self.assertEqual(len(payload["accessions"]), 1)
        self.assertFalse(payload["accessions"][0]["legal_movement_verified"])
        self.assertIn("does not prove", payload["semantic_note"])


if __name__ == "__main__":
    unittest.main()
