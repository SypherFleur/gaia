from __future__ import annotations

import unittest

from apps.api.gaia_api.runtime import AlphaProviderModes, cost_status, create_runtime, doctor_report, provider_health_rows


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
            self.assertEqual(rows["aphis"]["decision_source"], "fixture_jurisdiction_pack")
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


if __name__ == "__main__":
    unittest.main()
