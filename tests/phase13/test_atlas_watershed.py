from __future__ import annotations

import asyncio
import unittest

from packages.geospatial import USGSWatershedAdapter


NLDI_PAYLOAD = {
    "features": [
        {
            "properties": {
                "comid": "5781401",
                "name": "Colorado River",
                "reachcode": "12090205000123",
            }
        }
    ]
}


def run(coro):
    return asyncio.run(coro)


class USGSWatershedAdapterTest(unittest.TestCase):
    def test_normalizes_named_feature(self) -> None:
        live = USGSWatershedAdapter().normalize_feature_response(NLDI_PAYLOAD, "https://api.water.usgs.gov/nldi/linked-data/comid/position")

        self.assertEqual(live.status.status, "AVAILABLE")
        self.assertEqual(live.watershed, "Colorado River")
        self.assertEqual(live.provenance[0].provider, "usgs-nldi")
        self.assertEqual(live.provenance[0].external_record_id, "5781401")
        self.assertIn("USGS", live.provenance[0].attribution)

    def test_falls_back_to_reachcode_when_unnamed(self) -> None:
        payload = {"features": [{"properties": {"comid": "5781401", "reachcode": "12090205000123"}}]}
        live = USGSWatershedAdapter().normalize_feature_response(payload)

        self.assertEqual(live.status.status, "AVAILABLE")
        self.assertEqual(live.watershed, "12090205000123")

    def test_no_feature_is_unresolved_not_guessed(self) -> None:
        live = USGSWatershedAdapter().normalize_feature_response({"features": []})

        self.assertEqual(live.status.status, "UNRESOLVED")
        self.assertIsNone(live.watershed)

    def test_feature_without_identifier_is_unresolved(self) -> None:
        live = USGSWatershedAdapter().normalize_feature_response({"features": [{"properties": {}}]})

        self.assertEqual(live.status.status, "UNRESOLVED")
        self.assertIsNone(live.watershed)

    def test_request_reduces_coordinate_precision(self) -> None:
        url = USGSWatershedAdapter().request_url(30.26721899, -97.74312345)

        self.assertNotIn("30.26721899", url)
        self.assertNotIn("-97.74312345", url)
        self.assertIn("30.27", url)

    def test_unreachable_endpoint_fails_closed(self) -> None:
        adapter = USGSWatershedAdapter(base_url="http://127.0.0.1:9/nldi", timeout_seconds=0.2)
        result = run(adapter.resolve_watershed(30.2672, -97.7431))

        self.assertEqual(result.status.status, "UNAVAILABLE")
        self.assertTrue(str(result.status.reason).startswith("nldi_"))


if __name__ == "__main__":
    unittest.main()
