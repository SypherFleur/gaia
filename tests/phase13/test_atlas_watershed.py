from __future__ import annotations

import asyncio
import unittest

from packages.geospatial import USGSWatershedAdapter


WBD_PAYLOAD = {
    "features": [
        {
            "attributes": {
                "OBJECTID": 41221,
                "HUC12": "120902050403",
                "Name": "Shoal Creek-Colorado River",
                "States": "TX",
            }
        }
    ]
}


def run(coro):
    return asyncio.run(coro)


class USGSWatershedAdapterTest(unittest.TestCase):
    def test_normalizes_named_hydrologic_unit(self) -> None:
        live = USGSWatershedAdapter().normalize_feature_response(
            WBD_PAYLOAD, "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/6/query"
        )

        self.assertEqual(live.status.status, "AVAILABLE")
        self.assertEqual(live.watershed, "Shoal Creek-Colorado River")
        self.assertEqual(live.provenance[0].provider, "usgs-wbd")
        self.assertEqual(live.provenance[0].external_record_id, "120902050403")
        self.assertIn("USGS", live.provenance[0].attribution)

    def test_field_casing_is_matched_case_insensitively(self) -> None:
        payload = {"features": [{"attributes": {"NAME": "Austin-Travis Lakes", "huc8": "12090205"}}]}
        live = USGSWatershedAdapter().normalize_feature_response(payload)

        self.assertEqual(live.status.status, "AVAILABLE")
        self.assertEqual(live.watershed, "Austin-Travis Lakes")
        self.assertEqual(live.provenance[0].external_record_id, "12090205")

    def test_identifier_is_never_returned_as_a_watershed_name(self) -> None:
        """The NLDI-era bug: a feature with only a code answered with the code,
        so `5781313` shipped as a watershed name. A code is not a name."""
        payload = {"features": [{"attributes": {"HUC12": "120902050403", "OBJECTID": 41221}}]}
        live = USGSWatershedAdapter().normalize_feature_response(payload)

        self.assertEqual(live.status.status, "UNRESOLVED")
        self.assertIsNone(live.watershed)

    def test_no_feature_is_unresolved_not_guessed(self) -> None:
        live = USGSWatershedAdapter().normalize_feature_response({"features": []})

        self.assertEqual(live.status.status, "UNRESOLVED")
        self.assertIsNone(live.watershed)

    def test_arcgis_error_body_is_unavailable_not_no_coverage(self) -> None:
        """ArcGIS reports service failures as HTTP 200 with an error body.
        Reading that as an empty result set would turn an outage into a
        confident "no watershed here"."""
        live = USGSWatershedAdapter().normalize_feature_response({"error": {"code": 500, "message": "Unable to complete operation."}})

        self.assertEqual(live.status.status, "UNAVAILABLE")
        self.assertIn("500", str(live.status.reason))
        self.assertIsNone(live.watershed)

    def test_layer_is_discovered_as_the_most_specific_hydrologic_unit(self) -> None:
        catalog = {
            "layers": [
                {"id": 0, "name": "WBDLine"},
                {"id": 4, "name": "8-digit HU (Subbasin)"},
                {"id": 6, "name": "12-digit HU (Subwatershed)"},
                {"id": 5, "name": "10-digit HU (Watershed)"},
            ]
        }

        self.assertEqual(USGSWatershedAdapter.select_hydrologic_unit_layer(catalog), 6)

    def test_layer_discovery_returns_none_when_no_hu_layer_is_published(self) -> None:
        self.assertIsNone(USGSWatershedAdapter.select_hydrologic_unit_layer({"layers": [{"id": 0, "name": "WBDLine"}]}))

    def test_request_reduces_coordinate_precision(self) -> None:
        url = USGSWatershedAdapter().request_url(30.26721899, -97.74312345)

        self.assertNotIn("30.26721899", url)
        self.assertNotIn("-97.74312345", url)
        self.assertIn("30.27", url)

    def test_unreachable_endpoint_fails_closed(self) -> None:
        adapter = USGSWatershedAdapter(base_url="http://127.0.0.1:9/wbd/MapServer", timeout_seconds=0.2)
        result = run(adapter.resolve_watershed(30.2672, -97.7431))

        self.assertEqual(result.status.status, "UNAVAILABLE")
        self.assertTrue(str(result.status.reason).startswith("wbd_"))


if __name__ == "__main__":
    unittest.main()
