from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from apps.api.gaia_api.chat_api import post_chat
from apps.api.gaia_api.runtime import AlphaProviderModes, cost_status, create_runtime, doctor_report, provider_health_rows, seed_demo, set_active_location, source_reconciliation_report


class ProtocolThreeRuntimeTest(unittest.TestCase):
    def test_full_alpha_runtime_preserves_zero_spend_controls(self) -> None:
        runtime = create_runtime("sqlite:///:memory:", provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
        try:
            status = cost_status(runtime)

            self.assertEqual(status["configured_reserve"], 20.0)
            self.assertEqual(status["total_development_cash_spent"], 0.0)
            self.assertEqual(status["reserve_remaining"], 20.0)
            self.assertFalse(status["paid_providers_enabled"])
            self.assertFalse(status["automatic_paid_usage_enabled"])
            self.assertFalse(status["automatic_overage_enabled"])
            self.assertIsNotNone(runtime.orchestrator)
            self.assertIsNotNone(runtime.terra)
            self.assertIsNotNone(runtime.vision)
            self.assertIsNotNone(runtime.scholar)
            self.assertIsNotNone(runtime.season)
            self.assertIsNotNone(runtime.mercator)
        finally:
            runtime.close()

    def test_development_identity_is_stable_inside_runtime(self) -> None:
        runtime = create_runtime("sqlite:///:memory:", provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
        try:
            self.assertEqual(runtime.registry.get("future-paid-provider").enabled, False)
            self.assertEqual(runtime.repository.get_workspace(runtime.organization_id, runtime.workspace_id)["name"], "Alpha Workspace")
            self.assertIn("tx-austin", runtime.location_aliases)
            self.assertEqual(runtime.primary_location_id, runtime.location_aliases["tx-austin"])
        finally:
            runtime.close()

    def test_doctor_output_uses_pass_warn_fail_disabled_states_without_secrets(self) -> None:
        runtime = create_runtime("sqlite:///:memory:", provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
        try:
            report = doctor_report(runtime)
            states = {check["state"] for check in report["checks"]}

            self.assertEqual(report["provider_modes"]["gbif"], "fixture")
            self.assertTrue(states.issubset({"PASS", "WARN", "FAIL", "DISABLED"}))
            self.assertFalse(report["paid_providers_enabled"])
            self.assertFalse(report["automatic_paid_usage_enabled"])
            self.assertNotIn("SECRET", str(report).upper())
            self.assertNotIn("API_KEY", str(report).upper())
        finally:
            runtime.close()

    def test_explicit_free_live_regulatory_modes_are_read_only_probes(self) -> None:
        runtime = create_runtime(
            "sqlite:///:memory:",
            provider_modes=AlphaProviderModes(aphis="live", florida_fdacs="live", text_model="fixture", vision_model="fixture"),
        )
        try:
            rows = {row["provider_id"]: row for row in provider_health_rows(runtime)}

            self.assertEqual(rows["aphis"]["mode"], "live")
            self.assertEqual(rows["aphis"]["live_probe"], "read_only_official_pages")
            self.assertEqual(rows["aphis"]["decision_source"], "live_provenance_only_rules_unresolved")
            self.assertEqual(rows["florida-fdacs"]["mode"], "live")
            self.assertEqual(rows["florida-fdacs"]["live_probe"], "read_only_official_pages")
            self.assertFalse(cost_status(runtime)["paid_providers_enabled"])
        finally:
            runtime.close()

    def test_disabled_provider_health_and_mode_are_explicit(self) -> None:
        runtime = create_runtime("sqlite:///:memory:", provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
        try:
            rows = {row["provider_id"]: row for row in provider_health_rows(runtime)}

            self.assertEqual(rows["google-calendar"]["mode"], "disabled")
            self.assertEqual(rows["google-calendar"]["health"], "DISABLED")
            self.assertEqual(rows["plantnet"]["mode"], "disabled")
            self.assertEqual(rows["future-paid-provider"]["mode"], "disabled")
            self.assertEqual(rows["future-paid-provider"]["health"], "DISABLED")
            self.assertEqual(rows["future-paid-provider"]["billing_class"], "MANUAL_PAID")
        finally:
            runtime.close()

    def test_guidance_graph_wraps_existing_orchestrator(self) -> None:
        runtime = create_runtime("sqlite:///:memory:", provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
        try:
            graph = runtime.orchestrator.graph_summary()

            self.assertIn(graph["engine"], {"langgraph", "langgraph-compatible-local"})
            self.assertIn("reasoning", graph["nodes"])
            self.assertTrue(graph["legacy_orchestrator_preserved"])
            self.assertTrue(graph["services_wrapped_not_reimplemented"])
        finally:
            runtime.close()

    def test_file_backed_normal_runtime_does_not_activate_demo_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "gaia.sqlite3"
            runtime = create_runtime(f"sqlite:///{db_path}")
            try:
                self.assertIsNone(runtime.primary_location_id)
                self.assertEqual(runtime.provider_modes.gbif, "live")
                self.assertEqual(runtime.provider_modes.europe_pmc, "live")
                self.assertEqual(runtime.provider_modes.usda_soil, "disabled")
                self.assertEqual(runtime.location_aliases, {})
                self.assertEqual(runtime.repository.list_locations(runtime.organization_id), [])
            finally:
                runtime.close()

    def test_device_location_resolves_harris_without_travis_masquerade(self) -> None:
        runtime = create_runtime("sqlite:///:memory:", provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
        try:
            payload = run(
                set_active_location(
                    runtime,
                    source_kind="device",
                    label="Browser device",
                    latitude=29.7604,
                    longitude=-95.3698,
                    accuracy_m=1200,
                )
            )
            self.assertEqual(payload["active_location"]["source_kind"], "device")
            self.assertEqual(payload["active_location"]["admin2"], "Harris County")

            result = run(
                post_chat(
                    runtime.orchestrator,
                    runtime.context(request_id="phase13-location"),
                    message="What county am I in?",
                    location_id=runtime.primary_location_id,
                )
            )
            self.assertIn("Harris County", result["content"])
            self.assertIn("device-approved", result["content"])
            self.assertNotIn("Travis County", result["content"])
        finally:
            runtime.close()

    def test_disabled_provider_mode_does_not_execute_fixture_adapter(self) -> None:
        runtime = create_runtime(
            "sqlite:///:memory:",
            provider_modes=AlphaProviderModes(genesys_pgr="disabled", text_model="fixture", vision_model="fixture"),
        )
        try:
            result = run(runtime.botanist.search_germplasm(runtime.context(request_id="phase13-disabled"), "cowpea", limit=1))

            self.assertEqual(result.status, "denied")
            self.assertEqual(result.denial_reason, "provider_disabled")
            self.assertEqual(result.data, {})
        finally:
            runtime.close()

    def test_source_reconciliation_marks_kew_documented_only_and_zero_cash(self) -> None:
        runtime = create_runtime("sqlite:///:memory:", provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
        try:
            report = source_reconciliation_report(runtime)
            rows = {row["provider_id"]: row for row in report["rows"]}

            self.assertEqual(rows["kew-powo"]["source_state"], "documented-only")
            self.assertTrue(rows["kew-powo"]["attribution_required"])
            self.assertFalse(report["cash_status"]["paid_providers_enabled"])
        finally:
            runtime.close()

    def test_seed_demo_uses_isolated_demo_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "gaia.sqlite3"
            runtime = create_runtime(f"sqlite:///{db_path}", provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
            try:
                normal_workspace_id = runtime.workspace_id
                seed_demo(runtime)

                self.assertNotEqual(runtime.workspace_id, normal_workspace_id)
                self.assertEqual(runtime.repository.get_workspace(runtime.organization_id, runtime.workspace_id)["name"], "Demo Workspace")
                self.assertEqual(runtime.repository.list_user_plants(runtime.organization_id, normal_workspace_id), [])
                self.assertGreater(len(runtime.repository.list_user_plants(runtime.organization_id, runtime.workspace_id)), 0)
            finally:
                runtime.close()


def run(coro):
    import asyncio

    return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main()
