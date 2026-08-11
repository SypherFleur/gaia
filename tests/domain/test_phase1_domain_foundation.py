from __future__ import annotations

import unittest
from dataclasses import fields, is_dataclass

from packages.cost import zero_spend_policy
from packages.domain import (
    Action,
    CalendarBinding,
    EnvironmentalSnapshot,
    EvidenceClaim,
    GeoContext,
    GuidancePlan,
    Location,
    MediaAttachment,
    Membership,
    ModelRun,
    MovementCheck,
    Observation,
    Organization,
    Outcome,
    PlantEntity,
    RegulationRule,
    SeasonPlan,
    SourceRecord,
    User,
    UserPlant,
    Workspace,
)
from packages.persistence import GaiaRepository, connect_in_memory, initialize_schema
from packages.persistence.sqlite import TenantAccessError


class Phase1Fixture:
    def __init__(self) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)

        self.org_a = self.repo.create_organization(
            Organization(name="Org A", slug="org-a", retention_policy={"deletion_window_days": 30})
        )
        self.org_b = self.repo.create_organization(Organization(name="Org B", slug="org-b"))
        self.user_a = self.repo.create_user(User(external_auth_id="dev:user-a", display_name="User A"))
        self.user_b = self.repo.create_user(User(external_auth_id="dev:user-b", display_name="User B"))
        self.repo.create_membership(
            Membership(organization_id=self.org_a.id, user_id=self.user_a.id, role="owner")
        )
        self.repo.create_membership(
            Membership(organization_id=self.org_b.id, user_id=self.user_b.id, role="owner")
        )

        self.workspace_a = self.repo.create_workspace(
            Workspace(organization_id=self.org_a.id, name="Garden A", purpose="personal garden")
        )
        self.workspace_b = self.repo.create_workspace(
            Workspace(organization_id=self.org_b.id, name="Garden B", purpose="personal garden")
        )
        self.location_a = self.repo.create_location(
            Location(
                organization_id=self.org_a.id,
                label="Approximate Austin garden",
                latitude=30.2672,
                longitude=-97.7431,
                privacy_precision="approximate",
                exact_coordinates_authorized=True,
                timezone="America/Chicago",
                country_code="US",
                admin1="TX",
                admin2="Travis",
                county_fips="48453",
            )
        )
        self.location_b = self.repo.create_location(
            Location(
                organization_id=self.org_b.id,
                label="Approximate Dallas garden",
                latitude=32.7767,
                longitude=-96.797,
                privacy_precision="approximate",
                timezone="America/Chicago",
                country_code="US",
                admin1="TX",
                admin2="Dallas",
                county_fips="48113",
            )
        )
        self.plant_entity = self.repo.create_plant_entity(
            PlantEntity(
                scientific_name="Solanum lycopersicum",
                common_names=["tomato"],
                family="Solanaceae",
                genus="Solanum",
                species="lycopersicum",
                crop_group="vegetable",
            )
        )
        self.user_plant_a = self.repo.create_user_plant(
            UserPlant(
                organization_id=self.org_a.id,
                workspace_id=self.workspace_a.id,
                plant_entity_id=self.plant_entity.id,
                nickname="A tomato",
                location_id=self.location_a.id,
            )
        )
        self.user_plant_b = self.repo.create_user_plant(
            UserPlant(
                organization_id=self.org_b.id,
                workspace_id=self.workspace_b.id,
                plant_entity_id=self.plant_entity.id,
                nickname="B tomato",
                location_id=self.location_b.id,
            )
        )

    def close(self) -> None:
        self.connection.close()


class Phase1DomainFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase1Fixture()
        self.repo = self.fixture.repo

    def tearDown(self) -> None:
        self.fixture.close()

    def test_organization_a_cannot_read_organization_b_data(self) -> None:
        self.assertIsNone(
            self.repo.get_workspace(self.fixture.org_a.id, self.fixture.workspace_b.id)
        )
        self.assertIsNotNone(
            self.repo.get_workspace(self.fixture.org_b.id, self.fixture.workspace_b.id)
        )

    def test_organization_a_cannot_modify_organization_b_data(self) -> None:
        changed = self.repo.update_workspace_name(
            self.fixture.org_a.id,
            self.fixture.workspace_b.id,
            "stolen name",
        )

        self.assertFalse(changed)
        workspace_b = self.repo.get_workspace(self.fixture.org_b.id, self.fixture.workspace_b.id)
        self.assertEqual(workspace_b["name"], "Garden B")

    def test_workspace_ownership_is_enforced(self) -> None:
        with self.assertRaises(TenantAccessError):
            self.repo.create_user_plant(
                UserPlant(
                    organization_id=self.fixture.org_a.id,
                    workspace_id=self.fixture.workspace_b.id,
                    plant_entity_id=self.fixture.plant_entity.id,
                    nickname="cross-tenant plant",
                )
            )

    def test_plant_observation_and_media_metadata_cannot_cross_tenants(self) -> None:
        with self.assertRaises(TenantAccessError):
            self.repo.create_observation(
                Observation(
                    organization_id=self.fixture.org_a.id,
                    workspace_id=self.fixture.workspace_a.id,
                    user_plant_id=self.fixture.user_plant_b.id,
                    author_id=self.fixture.user_a.id,
                    text="Trying to attach an Org B plant to Org A.",
                )
            )

        observation_b = self.repo.create_observation(
            Observation(
                organization_id=self.fixture.org_b.id,
                workspace_id=self.fixture.workspace_b.id,
                user_plant_id=self.fixture.user_plant_b.id,
                author_id=self.fixture.user_b.id,
                text="Org B observation.",
            )
        )

        with self.assertRaises(TenantAccessError):
            self.repo.create_media_attachment(
                MediaAttachment(
                    organization_id=self.fixture.org_a.id,
                    workspace_id=self.fixture.workspace_a.id,
                    observation_id=observation_b.id,
                    modality="image",
                    storage_uri="local://org-a/not-allowed.jpg",
                    content_type="image/jpeg",
                    byte_size=100,
                )
            )

    def test_guidance_plan_provenance_relationships_remain_intact(self) -> None:
        source = self.repo.create_source_record(
            SourceRecord(
                organization_id=self.fixture.org_a.id,
                provider="fixture",
                source_type="weather",
                canonical_url="https://example.invalid/weather",
                title="Fixture weather source",
                license="unknown",
            )
        )
        evidence = self.repo.create_evidence_claim(
            EvidenceClaim(
                organization_id=self.fixture.org_a.id,
                claim_text="Forecast low is above tomato cold-stress threshold.",
                evidence_grade="B",
                confidence=0.86,
                source_record_ids=[source.id],
            )
        )
        model_run = self.repo.create_model_run(
            ModelRun(
                organization_id=self.fixture.org_a.id,
                provider="fixture-local",
                model="mock-structured-output",
                model_version="0",
                local_or_remote="local",
                cost_usd=0.0,
            )
        )
        guidance_plan = self.repo.create_guidance_plan(
            GuidancePlan(
                organization_id=self.fixture.org_a.id,
                workspace_id=self.fixture.workspace_a.id,
                subject="Tomato cold stress",
                situation="Night temperature question.",
                recommendations=[{"summary": "No frost action required tonight."}],
                evidence_claim_ids=[evidence.id],
                model_run_ids=[model_run.id],
            )
        )

        stored_plan = self.repo.get_guidance_plan(self.fixture.org_a.id, guidance_plan.id)
        links = self.repo.guidance_plan_evidence_links(self.fixture.org_a.id, guidance_plan.id)

        self.assertEqual(stored_plan["evidence_claim_ids"], [evidence.id])
        self.assertEqual(stored_plan["model_run_ids"], [model_run.id])
        self.assertEqual(links[0]["evidence_claim_id"], evidence.id)

    def test_guidance_plan_rejects_cross_tenant_evidence(self) -> None:
        evidence_b = self.repo.create_evidence_claim(
            EvidenceClaim(
                organization_id=self.fixture.org_b.id,
                claim_text="Org B private evidence.",
                evidence_grade="D",
                confidence=0.5,
            )
        )

        with self.assertRaises(TenantAccessError):
            self.repo.create_guidance_plan(
                GuidancePlan(
                    organization_id=self.fixture.org_a.id,
                    workspace_id=self.fixture.workspace_a.id,
                    subject="Cross-tenant provenance",
                    situation="Should fail.",
                    evidence_claim_ids=[evidence_b.id],
                )
            )

    def test_soft_deleted_objects_are_inaccessible_through_normal_queries(self) -> None:
        observation = self.repo.create_observation(
            Observation(
                organization_id=self.fixture.org_a.id,
                workspace_id=self.fixture.workspace_a.id,
                user_plant_id=self.fixture.user_plant_a.id,
                author_id=self.fixture.user_a.id,
                text="This should disappear from normal reads after soft deletion.",
            )
        )

        self.assertTrue(self.repo.soft_delete("observations", self.fixture.org_a.id, observation.id))
        self.assertIsNone(self.repo.get_observation(self.fixture.org_a.id, observation.id))

    def test_cost_policy_defaults_remain_zero_spend(self) -> None:
        policy = zero_spend_policy("fixture-local")

        self.assertEqual(policy.hard_monthly_usd, 0.0)
        self.assertFalse(policy.allow_overage)
        self.assertEqual(policy.billing_class, "LOCAL")

    def test_domain_models_do_not_require_external_api_keys(self) -> None:
        required_models = [
            Organization,
            User,
            Membership,
            Workspace,
            Location,
            GeoContext,
            PlantEntity,
            UserPlant,
            Observation,
            EnvironmentalSnapshot,
            EvidenceClaim,
            GuidancePlan,
            Action,
            Outcome,
            RegulationRule,
            MovementCheck,
            SeasonPlan,
            CalendarBinding,
            SourceRecord,
            ModelRun,
        ]

        for model in required_models:
            with self.subTest(model=model.__name__):
                self.assertTrue(is_dataclass(model))
                model()
                field_names = {field.name.lower() for field in fields(model)}
                self.assertFalse(any("api_key" in name or "secret" in name for name in field_names))


if __name__ == "__main__":
    unittest.main()
