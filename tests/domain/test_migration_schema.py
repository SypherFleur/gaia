from __future__ import annotations

import unittest

from packages.persistence import connect_in_memory, initialize_schema


class MigrationSchemaTest(unittest.TestCase):
    def test_core_domain_tables_exist(self) -> None:
        connection = connect_in_memory()
        initialize_schema(connection)

        expected_tables = {
            "organizations",
            "users",
            "memberships",
            "workspaces",
            "locations",
            "geo_contexts",
            "plant_entities",
            "user_plants",
            "observations",
            "media_attachments",
            "environmental_snapshots",
            "evidence_claims",
            "guidance_plans",
            "guidance_plan_evidence_claims",
            "guidance_plan_model_runs",
            "actions",
            "outcomes",
            "regulation_rules",
            "movement_checks",
            "season_plans",
            "calendar_bindings",
            "source_records",
            "model_runs",
            "usage_events",
            "audit_events",
            "cache_records",
            "source_snapshots",
            "atlas_zone_features",
            "prompt_harnesses",
            "conversations",
            "messages",
            "plant_profiles",
            "research_authors",
            "research_works",
            "research_claims",
            "evidence_syntheses",
            "research_collections",
            "research_annotations",
            "movement_requests",
            "movement_decisions",
            "sentinel_zone_features",
        }

        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        actual_tables = {row["name"] for row in rows}

        self.assertTrue(expected_tables.issubset(actual_tables))
        connection.close()

    def test_location_privacy_default_is_approximate(self) -> None:
        connection = connect_in_memory()
        initialize_schema(connection)

        columns = connection.execute("PRAGMA table_info(locations)").fetchall()
        defaults = {column["name"]: column["dflt_value"] for column in columns}

        self.assertEqual(defaults["privacy_precision"], "'approximate'")
        connection.close()


if __name__ == "__main__":
    unittest.main()
