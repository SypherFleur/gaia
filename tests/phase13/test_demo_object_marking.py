from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from apps.api.gaia_api.runtime import AlphaProviderModes, CLIGeographyProvider, create_runtime, seed_demo


def run(coro):
    return asyncio.run(coro)


class DemoObjectMarkingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.get("GAIA_ATLAS_GEOGRAPHY_MODE")
        os.environ["GAIA_ATLAS_GEOGRAPHY_MODE"] = "fixture"

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop("GAIA_ATLAS_GEOGRAPHY_MODE", None)
        else:
            os.environ["GAIA_ATLAS_GEOGRAPHY_MODE"] = self._previous

    def _seeded_runtime(self, directory: str):
        runtime = create_runtime(
            f"sqlite:///{Path(directory) / 'demo.sqlite3'}",
            provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"),
        )
        seed_demo(runtime)
        return runtime

    def test_seeded_plant_and_plan_are_marked_demo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = self._seeded_runtime(directory)
            try:
                plants = runtime.repository.list_user_plants(runtime.organization_id, runtime.workspace_id)
                plans = runtime.repository.list_season_plans(runtime.organization_id, runtime.workspace_id)

                self.assertTrue(plants, "seed should create a plant")
                self.assertTrue(plans, "seed should create a season plan")
                self.assertTrue(plants[0]["is_demo"], "seeded plant must be marked demo")
                self.assertTrue(plans[0]["is_demo"], "seeded plan must be marked demo")
            finally:
                runtime.close()

    def test_seeded_plan_window_is_derived_from_today_not_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = self._seeded_runtime(directory)
            try:
                plan = runtime.repository.list_season_plans(runtime.organization_id, runtime.workspace_id)[0]

                # A frozen window reads as a stale bug once it falls into the past.
                self.assertGreaterEqual(plan["start_date"], date.today().isoformat())
                self.assertNotEqual(plan["start_date"], "2026-09-15")
                self.assertNotEqual(plan["end_date"], "2026-12-15")
            finally:
                runtime.close()

    def test_user_created_objects_are_not_marked_demo(self) -> None:
        from apps.api.gaia_api.plant_api import post_plant

        with tempfile.TemporaryDirectory() as directory:
            runtime = self._seeded_runtime(directory)
            try:
                created = run(
                    post_plant(
                        runtime.repository,
                        runtime.botanist,
                        runtime.context(request_id="demo-marking"),
                        taxon_query="Solanum lycopersicum",
                        nickname="My own tomato",
                        location_id=runtime.primary_location_id,
                    )
                )

                self.assertFalse(created["plant"]["is_demo"], "a plant the user creates is not demo content")
            finally:
                runtime.close()


class OfflineGeographyDoesNotInventCountiesTest(unittest.TestCase):
    """The bounding-box table used to answer any nearby coordinate with a
    plausible county, and defaulted everything else to Travis County. Real
    geography must come from the Census geocoder."""

    def test_non_fixture_mode_never_resolves_a_county_offline(self) -> None:
        provider = CLIGeographyProvider(fixture=False)

        # Austin, an exact seeded demo coordinate — still unresolved, because
        # live geography is configured and nothing may stand in for it.
        result = run(provider.resolve_admin(30.2672, -97.7431))

        self.assertEqual(result.status.status, "UNAVAILABLE")
        self.assertIsNone(result.county_or_district)

    def test_fixture_mode_resolves_only_exact_demo_coordinates(self) -> None:
        provider = CLIGeographyProvider(fixture=True)

        austin = run(provider.resolve_admin(30.2672, -97.7431))
        self.assertEqual(austin.status.status, "AVAILABLE")
        self.assertEqual(austin.county_or_district, "Travis County")

    def test_fixture_mode_does_not_guess_for_a_nearby_coordinate(self) -> None:
        provider = CLIGeographyProvider(fixture=True)

        # ~5 km from the Houston demo point. The old bounding box answered
        # "Harris County" here; that is a geocode result it never earned.
        result = run(provider.resolve_admin(29.72, -95.4))

        self.assertEqual(result.status.status, "UNAVAILABLE")
        self.assertIsNone(result.county_or_district)

    def test_fixture_mode_does_not_default_unknown_coordinates_to_travis(self) -> None:
        provider = CLIGeographyProvider(fixture=True)

        result = run(provider.resolve_admin(51.5074, -0.1278))  # London

        self.assertEqual(result.status.status, "UNAVAILABLE")
        self.assertIsNone(result.county_or_district)


if __name__ == "__main__":
    unittest.main()
