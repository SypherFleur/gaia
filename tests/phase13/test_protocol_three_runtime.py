from __future__ import annotations

import unittest

from apps.api.gaia_api.runtime import AlphaProviderModes, cost_status, create_runtime, doctor_report


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


if __name__ == "__main__":
    unittest.main()
