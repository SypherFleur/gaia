from __future__ import annotations

import asyncio
import unittest

from packages.environment.live_adapters import USGSWaterApiAdapter
from packages.institutional import KnowledgeService
from packages.institutional.embeddings import FixtureEmbeddingProvider
from packages.domain import Membership, Organization, User, Workspace
from packages.persistence import GaiaRepository, connect_in_memory, initialize_schema
from packages.tools import ToolExecutionContext


NWIS_PAYLOAD = {
    "value": {
        "timeSeries": [
            {
                "sourceInfo": {"siteName": "Colorado Rv at Austin, TX", "siteCode": [{"value": "08158000"}]},
                "variable": {"variableCode": [{"value": "00060"}], "unit": {"unitCode": "ft3/s"}},
                "values": [{"value": [{"value": "412", "dateTime": "2026-08-15T12:00:00.000-05:00"}]}],
            },
            {
                "sourceInfo": {"siteName": "Colorado Rv at Austin, TX", "siteCode": [{"value": "08158000"}]},
                "variable": {"variableCode": [{"value": "00065"}], "unit": {"unitCode": "ft"}},
                "values": [{"value": [{"value": "4.31", "dateTime": "2026-08-15T12:00:00.000-05:00"}]}],
            },
            {
                "sourceInfo": {"siteName": "Dry Creek", "siteCode": [{"value": "08158100"}]},
                "variable": {"variableCode": [{"value": "00060"}], "unit": {"unitCode": "ft3/s"}},
                "values": [{"value": [{"value": "-999999", "dateTime": "2026-08-15T12:00:00.000-05:00"}]}],
            },
        ]
    }
}


def run(coro):
    return asyncio.run(coro)


class USGSWaterAdapterTest(unittest.TestCase):
    def test_normalizes_sites_and_latest_readings(self) -> None:
        live = USGSWaterApiAdapter().normalize_instantaneous_response(NWIS_PAYLOAD, "https://waterservices.usgs.gov/nwis/iv/")

        self.assertEqual(live.status, "AVAILABLE")
        austin = next(site for site in live.data["sites"] if site["site_no"] == "08158000")
        self.assertEqual(austin["name"], "Colorado Rv at Austin, TX")
        self.assertEqual(austin["measurements"]["discharge_cfs"]["value"], 412.0)
        self.assertEqual(austin["measurements"]["discharge_cfs"]["unit"], "ft3/s")
        self.assertEqual(austin["measurements"]["gage_height_ft"]["value"], 4.31)
        self.assertEqual(live.data["evidence_type"], "OBSERVED")
        self.assertIn("not field soil moisture", live.data["semantic_note"])
        self.assertEqual(live.provenance[0].provider, "usgs-water")

    def test_sentinel_no_data_values_are_dropped(self) -> None:
        live = USGSWaterApiAdapter().normalize_instantaneous_response(NWIS_PAYLOAD, mode="current")
        site_numbers = {site["site_no"] for site in live.data["sites"]}

        # -999999 is NWIS's "no reading"; that site has no usable measurement.
        self.assertNotIn("08158100", site_numbers)

    def test_empty_response_is_unavailable(self) -> None:
        live = USGSWaterApiAdapter().normalize_instantaneous_response({"value": {"timeSeries": []}})

        self.assertEqual(live.status, "UNAVAILABLE")
        self.assertIn("usgs_no_sites_in_search_area", live.warnings)

    def test_request_url_uses_reduced_bounding_box(self) -> None:
        url = USGSWaterApiAdapter().request_url(30.26721899, -97.74312345)

        self.assertIn("bBox=", url)
        self.assertNotIn("30.26721899", url)
        self.assertNotIn("-97.74312345", url)

    def test_historical_is_explicitly_unavailable_not_empty_success(self) -> None:
        result = run(USGSWaterApiAdapter().historical_conditions(30.2672, -97.7431))

        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertIn("usgs_historical_daily_values_not_implemented", result.warnings)

    def test_unreachable_endpoint_fails_closed(self) -> None:
        adapter = USGSWaterApiAdapter(base_url="http://127.0.0.1:9/nwis", timeout_seconds=0.2)
        result = run(adapter.nearby_sites(30.2672, -97.7431))

        self.assertEqual(result.status, "PROVIDER_ERROR")
        self.assertTrue(any(warning.startswith("usgs_") for warning in result.warnings))


class KnowledgeFTSRetrievalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Org", slug="fts-org"))
        self.user = self.repo.create_user(User(external_auth_id="dev:fts", display_name="FTS User"))
        self.repo.create_membership(
            Membership(
                organization_id=self.org.id,
                user_id=self.user.id,
                role="owner",
                permissions=["knowledge.create", "knowledge.ingest", "knowledge.search"],
            )
        )
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Lab", purpose="fts"))
        self.service = KnowledgeService(repository=self.repo, embedding_provider=FixtureEmbeddingProvider())
        self.collection = self.service.create_collection(self.context(), name="Agronomy", visibility="ORGANIZATION")

    def tearDown(self) -> None:
        self.connection.close()

    def context(self) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="fts-test",
            organization_id=self.org.id,
            user_id=self.user.id,
            workspace_id=self.workspace.id,
            permissions=frozenset({"knowledge.create", "knowledge.ingest", "knowledge.search"}),
        )

    def ingest(self, title: str, body: str):
        return run(self.service.ingest_document(self.context(), collection_id=self.collection.id, title=title, format="text", body=body))

    def test_ranked_retrieval_prefers_denser_matches(self) -> None:
        self.ingest("Irrigation depth", "Irrigation scheduling depends on irrigation frequency and irrigation depth for tomato beds.")
        self.ingest("Passing mention", "This note is mostly about trellising and mentions irrigation once.")

        results = self.service.search(self.context(), self.collection.id, "irrigation")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Irrigation depth")
        self.assertGreater(results[0]["score"], results[1]["score"])
        self.assertEqual(results[0]["retrieval"], "fts5_bm25")

    def test_stemming_matches_word_variants(self) -> None:
        self.ingest("Stemming", "Growers reported heavy watering across the season.")

        # Substring counting could never match "watering" from "water".
        self.assertTrue(self.service.search(self.context(), self.collection.id, "water"))

    def test_non_matching_query_returns_nothing(self) -> None:
        self.ingest("Irrigation", "Irrigation scheduling for tomato beds.")

        self.assertEqual(self.service.search(self.context(), self.collection.id, "quantum chromodynamics"), [])

    def test_fts_operators_in_user_input_are_treated_literally(self) -> None:
        self.ingest("Irrigation", "Irrigation scheduling for tomato beds.")

        # A raw MATCH would treat these as syntax and could error or over-match.
        self.assertEqual(self.service.search(self.context(), self.collection.id, "irrigation NOT tomato"), self.service.search(self.context(), self.collection.id, "irrigation not tomato"))
        self.assertEqual(self.service.search(self.context(), self.collection.id, '"'), [])
        self.assertEqual(self.service.search(self.context(), self.collection.id, "*"), [])

    def test_retrieval_is_tenant_scoped(self) -> None:
        self.ingest("Irrigation", "Irrigation scheduling for tomato beds.")

        other_org = self.repo.create_organization(Organization(name="Other", slug="fts-other"))
        other_user = self.repo.create_user(User(external_auth_id="dev:fts-other", display_name="Other"))
        self.repo.create_membership(
            Membership(organization_id=other_org.id, user_id=other_user.id, role="owner", permissions=["knowledge.search"])
        )
        other_workspace = self.repo.create_workspace(Workspace(organization_id=other_org.id, name="Other", purpose="fts"))
        other_context = ToolExecutionContext(
            request_id="fts-other",
            organization_id=other_org.id,
            user_id=other_user.id,
            workspace_id=other_workspace.id,
            permissions=frozenset({"knowledge.search"}),
        )

        with self.assertRaises(PermissionError):
            self.service.search(other_context, self.collection.id, "irrigation")


if __name__ == "__main__":
    unittest.main()
