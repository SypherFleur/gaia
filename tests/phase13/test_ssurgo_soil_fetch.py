from __future__ import annotations

import asyncio
import unittest

from packages.environment.fixture_adapters import FixtureUSDASoilProvider
from packages.environment.live_adapters import USDASoilDataAccessAdapter


COLUMN_NAMES = [
    "muname",
    "compname",
    "drainagecl",
    "hydgrp",
    "slope_l",
    "slope_h",
    "texture",
    "ph1to1h2o_r",
    "awc_r",
    "om_r",
    "resdept_r",
]

SDA_PAYLOAD = {
    "Table": [
        COLUMN_NAMES,
        ["Austin silty clay, 1 to 3 percent slopes", "Austin", "well drained", "D", "1.0", "3.0", "silty clay", "7.8", "0.17", "2.5", None],
    ]
}


def run(coro):
    return asyncio.run(coro)


class SSURGOSoilFetchTest(unittest.TestCase):
    def test_live_normalizer_matches_fixture_soil_contract(self) -> None:
        fixture = run(FixtureUSDASoilProvider().soil_context(30.2672, -97.7431))
        live = USDASoilDataAccessAdapter().normalize_mapunit_response(SDA_PAYLOAD, "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest")

        self.assertEqual(live.status, "AVAILABLE")
        self.assertEqual(set(live.data), set(fixture.data))
        self.assertEqual(live.data["component"], "Austin")
        self.assertEqual(live.data["drainage_class"], "well drained")
        self.assertEqual(live.data["hydrologic_soil_group"], "D")
        self.assertEqual(live.data["texture"]["value"], "silty clay")
        self.assertEqual(live.data["ph"]["value"], 7.8)
        self.assertEqual(live.data["slope"]["value"], "1-3%")
        self.assertIsNone(live.data["restrictive_depth"]["value"])
        self.assertIn("not live soil moisture", live.data["semantic_note"])
        self.assertEqual(live.provenance[0].provider, "usda-nrcs-sda")

    def test_dict_shaped_rows_are_also_accepted(self) -> None:
        payload = {"Table": [dict(zip(COLUMN_NAMES, SDA_PAYLOAD["Table"][1]))]}
        live = USDASoilDataAccessAdapter().normalize_mapunit_response(payload, "https://example.invalid")

        self.assertEqual(live.status, "AVAILABLE")
        self.assertEqual(live.data["component"], "Austin")

    def test_unmatched_point_is_unavailable_not_guessed(self) -> None:
        live = USDASoilDataAccessAdapter().normalize_mapunit_response({"Table": []}, "https://example.invalid")

        self.assertEqual(live.status, "UNAVAILABLE")
        self.assertNotIn("map_unit", live.data)
        self.assertIn("did not infer", live.data["semantic_note"])

    def test_query_reduces_coordinate_precision(self) -> None:
        query = USDASoilDataAccessAdapter().build_query(30.26721899, -97.74312345)

        self.assertIn("point(-97.7431 30.2672)", query)
        self.assertNotIn("30.26721899", query)
        self.assertNotIn("-97.74312345", query)

    def test_unreachable_endpoint_fails_closed(self) -> None:
        adapter = USDASoilDataAccessAdapter(base_url="http://127.0.0.1:9/Tabular/post.rest", timeout_seconds=0.2)
        result = run(adapter.soil_context(30.2672, -97.7431))

        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertTrue(str(result.data["semantic_note"]).startswith("ssurgo_"))


if __name__ == "__main__":
    unittest.main()
