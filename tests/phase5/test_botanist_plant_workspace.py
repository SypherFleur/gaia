from __future__ import annotations

import asyncio
import unittest

from apps.api.gaia_api.chat_api import post_chat
from apps.api.gaia_api.plant_api import (
    get_germplasm_search,
    get_observations,
    get_plant,
    get_plants,
    get_taxa_search,
    post_observation,
    post_plant,
)
from packages.audit import AuditLog, UsageLedger
from packages.botany import BotanistService, FixtureGBIFProvider, FixtureGenesysProvider, GBIFTaxonomyTool, GenesysGermplasmTool
from packages.cache import SQLiteCacheBackend
from packages.context import ContextCompiler
from packages.cost import CostFirewall
from packages.domain import Location, Membership, Organization, PlantEntity, User, UserPlant, Workspace
from packages.environment.fixture_adapters import FixtureNASAPowerProvider, FixtureNWSProvider, FixtureUSDASoilProvider, FixtureUSGSWaterProvider
from packages.environment.terra import TerraService
from packages.environment.tools import NASAPowerClimateTool, NWSForecastTool, USDASoilSurveyTool, USGSWaterSitesTool
from packages.geospatial import AtlasService
from packages.geospatial.providers import FixtureGeographyProvider, FixtureHardinessProvider, FixtureRegulatoryGeometryProvider, FixtureWatershedProvider
from packages.model_gateway import FixtureGuidanceModelProvider, ModelGateway
from packages.orchestration import GaiaOrchestrator
from packages.persistence import GaiaRepository, TenantAccessError, connect_in_memory, initialize_schema
from packages.providers import (
    AuthenticationRequirement,
    BillingClass,
    CachePolicy,
    FreshnessClass,
    LicenseMetadata,
    ProviderQuotaPolicy,
    ProviderRecord,
    ProviderRegistry,
    ProviderType,
    QuotaManager,
)
from packages.tools import ToolExecutionContext, ToolGateway


def run(coro):
    return asyncio.run(coro)


def enabled_provider(provider_id: str, provider_type: ProviderType, *, remote: bool = True) -> ProviderRecord:
    from packages.cost import ProviderCostPolicy

    billing_class = BillingClass.LOCAL if provider_type == ProviderType.MODEL else BillingClass.FREE
    return ProviderRecord(
        provider_id=provider_id,
        display_name=provider_id,
        provider_type=provider_type,
        authority=provider_id,
        enabled=True,
        billing_class=billing_class,
        cost_policy=ProviderCostPolicy(provider_id=provider_id, billing_class=billing_class.value, hard_monthly_usd=0.0, allow_overage=False),
        quota_policy=ProviderQuotaPolicy(daily_requests=100),
        authentication_requirement=AuthenticationRequirement.LOCAL_ONLY if not remote else AuthenticationRequirement.NONE,
        geographic_scope="fixture",
        cache_policy=CachePolicy(FreshnessClass.LONG, ttl_seconds=86400, stale_if_error_seconds=86400),
        license_metadata=LicenseMetadata(),
        attribution=provider_id,
        remote=remote,
    )


class Phase5Fixture:
    def __init__(self, *, gbif=None, genesys=None) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Org", slug="phase5-org"))
        self.user = self.repo.create_user(User(external_auth_id="dev:phase5", display_name="Phase 5 User"))
        self.repo.create_membership(Membership(organization_id=self.org.id, user_id=self.user.id, role="owner", permissions=["tool.read", "model.chat"]))
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Garden", purpose="phase5"))
        self.location = self.repo.create_location(
            Location(
                organization_id=self.org.id,
                label="Austin garden",
                latitude=30.2672,
                longitude=-97.7431,
                privacy_precision="1km",
                exact_coordinates_authorized=True,
                timezone="America/Chicago",
                country_code="US",
            )
        )
        self.other_org = self.repo.create_organization(Organization(name="Other", slug="phase5-other"))
        self.other_user = self.repo.create_user(User(external_auth_id="dev:phase5-other", display_name="Other User"))
        self.repo.create_membership(Membership(organization_id=self.other_org.id, user_id=self.other_user.id, role="owner", permissions=["tool.read", "model.chat"]))
        self.other_workspace = self.repo.create_workspace(Workspace(organization_id=self.other_org.id, name="Other Garden", purpose="phase5"))
        self.other_location = self.repo.create_location(Location(organization_id=self.other_org.id, label="Other", latitude=31.0, longitude=-98.0, timezone="America/Chicago"))
        self.registry = ProviderRegistry(
            [
                enabled_provider("nws", ProviderType.WEATHER),
                enabled_provider("nasa-power", ProviderType.CLIMATE),
                enabled_provider("usda-nrcs-sda", ProviderType.SOIL),
                enabled_provider("usgs-water", ProviderType.WATER),
                enabled_provider("gbif", ProviderType.TAXONOMY),
                enabled_provider("genesys-pgr", ProviderType.GERMPLASM),
                enabled_provider("ollama-local", ProviderType.MODEL, remote=False),
            ]
        )
        self.ledger = UsageLedger(self.connection)
        self.audit = AuditLog(self.connection)
        self.cache = SQLiteCacheBackend(self.connection)
        self.gateway = ToolGateway(
            connection=self.connection,
            registry=self.registry,
            cost_firewall=CostFirewall(),
            quota_manager=QuotaManager(self.connection),
            cache_backend=self.cache,
            usage_ledger=self.ledger,
            audit_log=self.audit,
        )
        self.gbif = gbif or FixtureGBIFProvider()
        self.genesys = genesys or FixtureGenesysProvider()
        self.botanist = BotanistService(
            self.repo,
            self.gateway,
            GBIFTaxonomyTool(self.gbif),
            GenesysGermplasmTool(self.genesys),
        )
        self.atlas = AtlasService(self.repo, FixtureGeographyProvider(), FixtureWatershedProvider(), FixtureHardinessProvider(), FixtureRegulatoryGeometryProvider())
        self.terra = TerraService(
            self.repo,
            self.gateway,
            NWSForecastTool(FixtureNWSProvider()),
            NASAPowerClimateTool(FixtureNASAPowerProvider()),
            USDASoilSurveyTool(FixtureUSDASoilProvider()),
            USGSWaterSitesTool(FixtureUSGSWaterProvider()),
        )
        self.model = FixtureGuidanceModelProvider()
        self.model_gateway = ModelGateway(
            connection=self.connection,
            registry=self.registry,
            providers={"ollama-local": self.model},
            cost_firewall=CostFirewall(),
            usage_ledger=self.ledger,
            audit_log=self.audit,
        )
        self.orchestrator = GaiaOrchestrator(
            repository=self.repo,
            context_compiler=ContextCompiler(self.repo, self.atlas, self.terra),
            model_gateway=self.model_gateway,
            botanist=self.botanist,
        )

    def context(self, *, org=None, user=None, workspace=None, permissions=frozenset({"tool.read", "model.chat"})) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="phase5",
            organization_id=(org or self.org).id,
            user_id=(user or self.user).id,
            workspace_id=(workspace or self.workspace).id,
            permissions=permissions,
        )

    def create_tomato_user_plant(self) -> UserPlant:
        lookup = run(self.botanist.resolve_taxon(self.context(), "Solanum lycopersicum"))
        self.botanist.build_plant_profile(self.org.id, lookup.plant_entity)
        return self.repo.create_user_plant(
            UserPlant(
                organization_id=self.org.id,
                workspace_id=self.workspace.id,
                plant_entity_id=lookup.plant_entity.id,
                nickname="Patio tomato",
                cultivar="Cherokee Purple",
                lifecycle_stage="vegetative",
                location_id=self.location.id,
                tags=["patio"],
            )
        )

    def model_run_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM model_runs").fetchone()
        return int(row["count"])

    def close(self) -> None:
        self.connection.close()


class BotanistPlantWorkspaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase5Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_accepted_taxon_resolves_to_canonical_entity_with_provenance(self) -> None:
        result = run(self.fixture.botanist.resolve_taxon(self.fixture.context(), "Solanum lycopersicum"))

        self.assertEqual(result.status, "ACCEPTED")
        self.assertEqual(result.plant_entity.scientific_name, "Solanum lycopersicum")
        self.assertEqual(result.plant_entity.family, "Solanaceae")
        self.assertTrue(result.source_record_ids)
        self.assertEqual(result.plant_entity.canonical_name_source_record_id, result.source_record_ids[0])

    def test_synonym_resolves_to_same_canonical_entity_without_merging_cultivar(self) -> None:
        accepted = run(self.fixture.botanist.resolve_taxon(self.fixture.context(), "Solanum lycopersicum"))
        synonym = run(self.fixture.botanist.resolve_taxon(self.fixture.context(), "Lycopersicon esculentum"))
        user_plant = self.fixture.repo.create_user_plant(
            UserPlant(
                organization_id=self.fixture.org.id,
                workspace_id=self.fixture.workspace.id,
                plant_entity_id=synonym.plant_entity.id,
                nickname="Heirloom",
                cultivar="Cherokee Purple",
                location_id=self.fixture.location.id,
            )
        )

        self.assertEqual(synonym.status, "SYNONYM")
        self.assertEqual(synonym.plant_entity.id, accepted.plant_entity.id)
        self.assertEqual(synonym.plant_entity.species, "lycopersicum")
        self.assertEqual(user_plant.cultivar, "Cherokee Purple")
        self.assertNotEqual(user_plant.cultivar, synonym.plant_entity.scientific_name)

    def test_ambiguous_common_name_does_not_silently_choose_species(self) -> None:
        result = run(get_taxa_search(self.fixture.botanist, self.fixture.context(), "mint"))

        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertIsNone(result["plant_entity"])
        self.assertGreaterEqual(len(result["alternatives"]), 2)

    def test_unknown_taxon_returns_unresolved_safely(self) -> None:
        result = run(get_taxa_search(self.fixture.botanist, self.fixture.context(), "Notaplant imaginaryensis"))

        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertIsNone(result["plant_entity"])

    def test_user_plant_cannot_reference_another_org_workspace_or_location(self) -> None:
        lookup = run(self.fixture.botanist.resolve_taxon(self.fixture.context(), "tomato"))
        with self.assertRaises(TenantAccessError):
            self.fixture.repo.create_user_plant(
                UserPlant(
                    organization_id=self.fixture.org.id,
                    workspace_id=self.fixture.other_workspace.id,
                    plant_entity_id=lookup.plant_entity.id,
                    nickname="bad workspace",
                )
            )
        with self.assertRaises(TenantAccessError):
            self.fixture.repo.create_user_plant(
                UserPlant(
                    organization_id=self.fixture.org.id,
                    workspace_id=self.fixture.workspace.id,
                    plant_entity_id=lookup.plant_entity.id,
                    nickname="bad location",
                    location_id=self.fixture.other_location.id,
                )
            )

    def test_observation_cannot_attach_to_another_tenant_plant(self) -> None:
        plant = self.fixture.create_tomato_user_plant()
        with self.assertRaises(TenantAccessError):
            self.fixture.repo.create_observation(
                __import__("packages.domain", fromlist=["Observation"]).Observation(
                    organization_id=self.fixture.other_org.id,
                    workspace_id=self.fixture.other_workspace.id,
                    user_plant_id=plant.id,
                    author_id=self.fixture.other_user.id,
                    text="cross tenant",
                )
            )

    def test_plant_workspace_queries_are_tenant_scoped(self) -> None:
        plant = self.fixture.create_tomato_user_plant()

        self.assertEqual(len(run(get_plants(self.fixture.repo, self.fixture.context()))), 1)
        self.assertIsNone(run(get_plant(self.fixture.repo, self.fixture.context(org=self.fixture.other_org, user=self.fixture.other_user, workspace=self.fixture.other_workspace), plant.id)))

    def test_plant_profile_fields_retain_provenance_and_conflicts(self) -> None:
        lookup = run(self.fixture.botanist.resolve_taxon(self.fixture.context(), "tomato"))
        profile = self.fixture.botanist.build_plant_profile(
            self.fixture.org.id,
            lookup.plant_entity,
            extra_conflicts=[{"field": "common_names", "values": ["tomato", "love apple"], "sources": ["fixture-a", "fixture-b"]}],
        )

        self.assertEqual(profile.field_provenance["scientific_name"]["provider"], "gbif")
        self.assertEqual(profile.field_provenance["scientific_name"]["source_record_id"], lookup.source_record_ids[0])
        self.assertEqual(profile.conflicts[0]["field"], "common_names")

    def test_genesys_results_retain_accession_provenance_and_caveats(self) -> None:
        result = run(get_germplasm_search(self.fixture.botanist, self.fixture.context(), "heat tolerant cowpea"))
        accession = result["accessions"][0]

        self.assertEqual(accession["accession_number"], "TVu-12345")
        self.assertFalse(accession["legal_movement_verified"])
        self.assertFalse(accession["availability_verified"])
        self.assertIn("does not prove", result["semantic_note"])

    def test_trait_information_is_not_invented_if_absent(self) -> None:
        fixture = Phase5Fixture(genesys=FixtureGenesysProvider(include_traits=False))
        try:
            result = run(get_germplasm_search(fixture.botanist, fixture.context(), "heat tolerant cowpea"))
            self.assertEqual(result["accessions"][0]["traits"], [])
        finally:
            fixture.close()

    def test_ask_gaia_about_this_plant_injects_correct_context_and_records_model_only_for_reasoning(self) -> None:
        plant = self.fixture.create_tomato_user_plant()
        run(
            post_observation(
                self.fixture.repo,
                self.fixture.context(),
                plant.id,
                text="Three lower leaves have yellow margins.",
                observed_facts=[{"fact": "Three lower leaves have yellow margins."}],
                gaia_inferences=[{"hypothesis": "Possible potassium deficiency", "confidence": 0.3}],
                health_tags=["yellowing"],
            )
        )
        botanist_context = run(self.fixture.botanist.build_context(self.fixture.context(), plant.id))
        self.assertEqual(botanist_context.model_run_count, 0)
        self.assertEqual(botanist_context.cultivar, "Cherokee Purple")

        result = run(
            post_chat(
                self.fixture.orchestrator,
                self.fixture.context(),
                message="Should I water this plant today?",
                location_id=self.fixture.location.id,
                user_plant_id=plant.id,
            )
        )

        self.assertEqual(result["route"], "reasoning")
        self.assertEqual(result["model_run_count"], 1)
        self.assertEqual(self.fixture.model_run_count(), 1)
        self.assertIn("Patio tomato", self.fixture.model.last_request.messages[1].content)
        plan = self.fixture.repo.get_guidance_plan(self.fixture.org.id, result["guidance_plan_id"])
        self.assertEqual(plan["user_plant_id"], plant.id)

    def test_another_tenant_plant_context_cannot_leak_into_conversation(self) -> None:
        plant = self.fixture.create_tomato_user_plant()
        with self.assertRaises(PermissionError):
            run(self.fixture.botanist.build_context(self.fixture.context(org=self.fixture.other_org, user=self.fixture.other_user, workspace=self.fixture.other_workspace), plant.id))

    def test_gbif_and_genesys_calls_pass_cost_firewall_and_no_paid_fallback_exists(self) -> None:
        run(self.fixture.botanist.resolve_taxon(self.fixture.context(), "tomato"))
        run(self.fixture.botanist.search_germplasm(self.fixture.context(), "heat tolerant cowpea"))
        usage = self.fixture.ledger.organization_usage(self.fixture.org.id)

        self.assertTrue(all(event["estimated_cost_usd"] == 0.0 for event in usage))
        self.assertNotIn("future-paid-provider", {event["provider_id"] for event in usage})

    def test_cached_botanical_facts_avoid_unnecessary_provider_calls(self) -> None:
        run(self.fixture.botanist.resolve_taxon(self.fixture.context(), "tomato"))
        run(self.fixture.botanist.resolve_taxon(self.fixture.context(), "tomato"))

        self.assertEqual(self.fixture.gbif.calls, 1)
        usage = self.fixture.ledger.organization_usage(self.fixture.org.id)
        self.assertEqual(usage[-1]["status"], "cache_hit")

    def test_gbif_outage_does_not_break_existing_plant_workspace(self) -> None:
        plant = self.fixture.create_tomato_user_plant()
        outage = Phase5Fixture(gbif=FixtureGBIFProvider(unavailable=True))
        try:
            # Existing record access remains local even when new taxonomy lookup fails.
            copied_entity = outage.repo.create_plant_entity(PlantEntity(scientific_name="Solanum lycopersicum", canonical_taxon_id="gbif:2930137", common_names=["tomato"]))
            copied = outage.repo.create_user_plant(UserPlant(organization_id=outage.org.id, workspace_id=outage.workspace.id, plant_entity_id=copied_entity.id, nickname=plant.nickname))
            self.assertIsNotNone(run(get_plant(outage.repo, outage.context(), copied.id)))
            unresolved = run(get_taxa_search(outage.botanist, outage.context(), "new plant"))
            self.assertEqual(unresolved["status"], "PROVIDER_ERROR")
        finally:
            outage.close()

    def test_genesys_outage_does_not_break_normal_plant_care_reasoning(self) -> None:
        fixture = Phase5Fixture(genesys=FixtureGenesysProvider(unavailable=True))
        try:
            plant = fixture.create_tomato_user_plant()
            germplasm = run(get_germplasm_search(fixture.botanist, fixture.context(), "heat tolerant cowpea"))
            result = run(post_chat(fixture.orchestrator, fixture.context(), message="Should I water this plant today?", location_id=fixture.location.id, user_plant_id=plant.id))
            self.assertEqual(germplasm["status"], "PROVIDER_ERROR")
            self.assertEqual(result["route"], "reasoning")
            self.assertEqual(result["model_run_count"], 1)
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
