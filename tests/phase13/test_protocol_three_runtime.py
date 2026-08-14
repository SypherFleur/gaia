from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from apps.api.gaia_api.chat_api import post_chat
from apps.api.gaia_api.runtime import (
    AlphaProviderModes,
    architecture_summary,
    cost_status,
    create_runtime,
    doctor_report,
    locations_payload,
    provider_health_rows,
    seed_cli_locations,
    seed_demo,
    set_active_location,
    source_reconciliation_report,
)


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
                architecture = architecture_summary(runtime)
                self.assertIsNone(architecture["location"]["active_location"])
                self.assertEqual(architecture["location"]["locations"], [])
            finally:
                runtime.close()

    def test_no_location_chat_requires_location_and_creates_zero_model_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "gaia.sqlite3"
            runtime = create_runtime(f"sqlite:///{db_path}")
            try:
                result = run(
                    post_chat(
                        runtime.orchestrator,
                        runtime.context(request_id="phase13-no-location"),
                        message="What county am I in?",
                        location_id=runtime.primary_location_id,
                    )
                )

                self.assertEqual(result["route"], "location_required")
                self.assertEqual(result["model_run_count"], 0)
                self.assertEqual(_model_run_count(runtime), 0)
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
            self.assertEqual(payload["active_location"]["accuracy_m"], 1200)
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

    def test_device_location_uses_atlas_and_persists_geography(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "gaia.sqlite3"
            runtime = create_runtime(f"sqlite:///{db_path}")
            try:
                payload = run(
                    set_active_location(
                        runtime,
                        source_kind="device",
                        label="Browser device",
                        latitude=29.7604,
                        longitude=-95.3698,
                        accuracy_m=42,
                    )
                )
                location = payload["active_location"]
                geo_rows = runtime.connection.execute(
                    "SELECT state_code, county_or_district, county_fips FROM geo_contexts WHERE organization_id = ? AND location_id = ?",
                    (runtime.organization_id, location["id"]),
                ).fetchall()

                self.assertEqual(location["source_kind"], "device")
                self.assertEqual(location["admin1"], "TX")
                self.assertEqual(location["admin2"], "Harris County")
                self.assertEqual(location["county_fips"], "48201")
                self.assertEqual(len(geo_rows), 1)
                self.assertEqual(geo_rows[0]["county_or_district"], "Harris County")
                self.assertEqual(locations_payload(runtime)["active_location"]["source_kind"], "device")
            finally:
                runtime.close()

    def test_reference_locations_are_hidden_and_inactive_in_normal_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "gaia.sqlite3"
            database = f"sqlite:///{db_path}"
            runtime = create_runtime(database)
            try:
                aliases = seed_cli_locations(runtime.repository, runtime.organization_id)
                runtime.repository.set_workspace_default_location(runtime.organization_id, runtime.workspace_id, aliases["tx-austin"])
            finally:
                runtime.close()

            restarted = create_runtime(database)
            try:
                payload = locations_payload(restarted)

                self.assertIsNone(restarted.primary_location_id)
                self.assertEqual(restarted.location_aliases, {})
                self.assertIsNone(payload["active_location"])
                self.assertEqual(payload["locations"], [])
                self.assertEqual(payload["location_aliases"], {})
            finally:
                restarted.close()

    def test_demo_locations_remain_isolated_from_normal_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "gaia.sqlite3"
            database = f"sqlite:///{db_path}"
            runtime = create_runtime(database, provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
            try:
                normal_workspace_id = runtime.workspace_id
                seed_demo(runtime)
                demo_locations = runtime.repository.list_locations(runtime.organization_id)

                self.assertTrue(demo_locations)
                self.assertTrue(all(location["source_kind"] == "demo_fixture" for location in demo_locations))
                self.assertTrue(all(bool(location["is_demo"]) for location in demo_locations))
            finally:
                runtime.close()

            restarted = create_runtime(database)
            try:
                self.assertEqual(restarted.workspace_id, normal_workspace_id)
                self.assertIsNone(restarted.primary_location_id)
                self.assertEqual(locations_payload(restarted)["locations"], [])
            finally:
                restarted.close()

    def test_saved_location_does_not_override_new_device_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "gaia.sqlite3"
            database = f"sqlite:///{db_path}"
            runtime = create_runtime(database)
            try:
                saved = run(
                    set_active_location(
                        runtime,
                        source_kind="saved",
                        label="Saved real location",
                        latitude=29.72,
                        longitude=-95.4,
                        accuracy_m=800,
                    )
                )
                device = run(
                    set_active_location(
                        runtime,
                        source_kind="device",
                        label="Current browser device",
                        latitude=29.7604,
                        longitude=-95.3698,
                        accuracy_m=35,
                    )
                )

                self.assertEqual(saved["active_location"]["source_kind"], "saved")
                self.assertEqual(device["active_location"]["source_kind"], "device")
                self.assertEqual(runtime.primary_location_id, device["active_location"]["id"])
            finally:
                runtime.close()

            restarted = create_runtime(database)
            try:
                active = locations_payload(restarted)["active_location"]

                self.assertIsNotNone(active)
                self.assertEqual(active["source_kind"], "device")
                self.assertEqual(active["admin2"], "Harris County")
            finally:
                restarted.close()

    def test_restart_preserves_explicit_saved_real_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "gaia.sqlite3"
            database = f"sqlite:///{db_path}"
            runtime = create_runtime(database)
            try:
                saved = run(
                    set_active_location(
                        runtime,
                        source_kind="saved",
                        label="Home garden",
                        latitude=29.7604,
                        longitude=-95.3698,
                        accuracy_m=250,
                    )
                )
                saved_id = saved["active_location"]["id"]
            finally:
                runtime.close()

            restarted = create_runtime(database)
            try:
                payload = locations_payload(restarted)

                self.assertEqual(restarted.primary_location_id, saved_id)
                self.assertEqual(payload["active_location"]["source_kind"], "saved")
                self.assertEqual(payload["active_location"]["admin2"], "Harris County")
                self.assertEqual(len(payload["locations"]), 1)
            finally:
                restarted.close()

    def test_unknown_normal_coordinate_does_not_fall_back_to_travis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "gaia.sqlite3"
            runtime = create_runtime(f"sqlite:///{db_path}")
            try:
                with self.assertRaisesRegex(ValueError, "location_resolution_unavailable"):
                    run(
                        set_active_location(
                            runtime,
                            source_kind="device",
                            label="Unknown coordinate",
                            latitude=40.7128,
                            longitude=-74.0060,
                            accuracy_m=50,
                        )
                    )
                self.assertEqual(locations_payload(runtime)["locations"], [])
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


def _model_run_count(runtime) -> int:
    row = runtime.connection.execute("SELECT COUNT(*) AS count FROM model_runs").fetchone()
    return int(row["count"])


if __name__ == "__main__":
    unittest.main()
