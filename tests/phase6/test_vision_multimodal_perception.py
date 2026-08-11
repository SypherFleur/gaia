from __future__ import annotations

import asyncio
import unittest

from packages.audit import AuditLog, UsageLedger
from packages.botany import BotanistService, FixtureGBIFProvider, FixtureGenesysProvider, GBIFTaxonomyTool, GenesysGermplasmTool
from packages.cache import SQLiteCacheBackend
from packages.context import ContextCompiler
from packages.cost import CostFirewall, ProviderCostPolicy
from packages.domain import Location, Membership, Organization, User, UserPlant, Workspace
from packages.environment.fixture_adapters import FixtureNASAPowerProvider, FixtureNWSProvider, FixtureUSDASoilProvider, FixtureUSGSWaterProvider
from packages.environment.terra import TerraService
from packages.environment.tools import NASAPowerClimateTool, NWSForecastTool, USDASoilSurveyTool, USGSWaterSitesTool
from packages.geospatial import AtlasService
from packages.geospatial.providers import FixtureGeographyProvider, FixtureHardinessProvider, FixtureRegulatoryGeometryProvider, FixtureWatershedProvider
from packages.persistence import GaiaRepository, TenantAccessError, connect_in_memory, initialize_schema
from packages.policy import DataEgressPolicy
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
from packages.vision import (
    FixturePlantNetProvider,
    FixtureVisionProvider,
    PlantNetAdapter,
    PlantNetIdentifyTool,
    VisionAnalysisTool,
    VisionService,
    normalize_plantnet_identification,
    validate_visual_response,
)
from packages.vision.validation import VisionValidationError


TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def run(coro):
    return asyncio.run(coro)


def enabled_provider(provider_id: str, provider_type: ProviderType, *, remote: bool = True, billing_class: BillingClass | None = None) -> ProviderRecord:
    billing = billing_class or (BillingClass.LOCAL if not remote else BillingClass.FREE)
    return ProviderRecord(
        provider_id=provider_id,
        display_name=provider_id,
        provider_type=provider_type,
        authority=provider_id,
        enabled=True,
        billing_class=billing,
        cost_policy=ProviderCostPolicy(provider_id=provider_id, billing_class=billing.value, hard_monthly_usd=0.0, allow_overage=False),
        quota_policy=ProviderQuotaPolicy(daily_requests=100),
        authentication_requirement=AuthenticationRequirement.LOCAL_ONLY if not remote else AuthenticationRequirement.OPTIONAL_API_KEY,
        geographic_scope="fixture",
        cache_policy=CachePolicy(FreshnessClass.LONG, ttl_seconds=86400, stale_if_error_seconds=86400),
        license_metadata=LicenseMetadata(),
        attribution=provider_id,
        remote=remote,
    )


class Phase6Fixture:
    def __init__(self, *, vision_provider=None) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Org", slug="phase6-org"))
        self.user = self.repo.create_user(User(external_auth_id="dev:phase6", display_name="Phase 6 User"))
        self.repo.create_membership(
            Membership(
                organization_id=self.org.id,
                user_id=self.user.id,
                role="owner",
                permissions=["tool.read", "model.chat", "vision.analyze"],
            )
        )
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Garden", purpose="phase6"))
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
        self.other_org = self.repo.create_organization(Organization(name="Other", slug="phase6-other"))
        self.other_user = self.repo.create_user(User(external_auth_id="dev:phase6-other", display_name="Other User"))
        self.repo.create_membership(Membership(organization_id=self.other_org.id, user_id=self.other_user.id, role="owner", permissions=["tool.read", "vision.analyze"]))
        self.other_workspace = self.repo.create_workspace(Workspace(organization_id=self.other_org.id, name="Other Garden", purpose="phase6"))
        self.registry = ProviderRegistry(
            [
                enabled_provider("nws", ProviderType.WEATHER),
                enabled_provider("nasa-power", ProviderType.CLIMATE),
                enabled_provider("usda-nrcs-sda", ProviderType.SOIL),
                enabled_provider("usgs-water", ProviderType.WATER),
                enabled_provider("gbif", ProviderType.TAXONOMY),
                enabled_provider("genesys-pgr", ProviderType.GERMPLASM),
                enabled_provider("fixture-vision-local", ProviderType.VISION, remote=False),
                enabled_provider("plantnet", ProviderType.VISION),
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
        self.botanist = BotanistService(
            self.repo,
            self.gateway,
            GBIFTaxonomyTool(FixtureGBIFProvider()),
            GenesysGermplasmTool(FixtureGenesysProvider()),
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
        self.vision_provider = vision_provider or FixtureVisionProvider()
        self.vision_tool = VisionAnalysisTool(self.vision_provider)
        self.plantnet_provider = FixturePlantNetProvider()
        self.plantnet_tool = PlantNetIdentifyTool(self.plantnet_provider)
        self.vision = VisionService(
            repository=self.repo,
            tool_gateway=self.gateway,
            context_compiler=ContextCompiler(self.repo, self.atlas, self.terra),
            botanist=self.botanist,
        )

    def context(
        self,
        *,
        org=None,
        user=None,
        workspace=None,
        permissions=frozenset({"tool.read", "model.chat", "vision.analyze"}),
        egress_policy=None,
    ) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="phase6",
            organization_id=(org or self.org).id,
            user_id=(user or self.user).id,
            workspace_id=(workspace or self.workspace).id,
            permissions=permissions,
            data_egress_policy=egress_policy or DataEgressPolicy(),
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
            )
        )

    def create_media(self, user_plant_id: str | None = None):
        return run(
            self.vision.create_image_attachment(
                self.context(),
                image_base64=TINY_PNG_BASE64,
                content_type="image/png",
                user_plant_id=user_plant_id,
            )
        )

    def model_run_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM model_runs").fetchone()
        return int(row["count"])

    def close(self) -> None:
        self.connection.close()


class VisionMultimodalPerceptionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase6Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_provider_neutral_capabilities_include_phase6_modes(self) -> None:
        capabilities = run(self.fixture.vision_provider.capabilities())

        self.assertTrue(capabilities.plant_identification)
        self.assertTrue(capabilities.symptom_description)
        self.assertTrue(capabilities.image_quality_assessment)
        self.assertEqual(capabilities.cost_class, "LOCAL")

    def test_visual_analysis_persists_observations_and_cautious_hypotheses(self) -> None:
        plant = self.fixture.create_tomato_user_plant()
        media = self.fixture.create_media(plant.id)

        result = run(
            self.fixture.vision.analyze_attachment(
                self.fixture.context(),
                tool=self.fixture.vision_tool,
                media_attachment_id=media.id,
                user_plant_id=plant.id,
                location_id=self.fixture.location.id,
            )
        )

        analysis = self.fixture.repo.get_visual_analysis(self.fixture.org.id, result.visual_analysis.id)
        self.assertEqual(analysis["status"], "AVAILABLE")
        self.assertEqual(analysis["user_plant_id"], plant.id)
        self.assertTrue(analysis["geo_context_id"])
        self.assertTrue(analysis["environmental_snapshot_id"])
        self.assertTrue(analysis["source_record_ids"])
        self.assertEqual(analysis["botanist_context"]["user_plant"]["nickname"], "Patio tomato")
        self.assertEqual(analysis["visual_observations"][0]["evidence_role"], "visual_observation")
        self.assertEqual(analysis["visual_hypotheses"][0]["evidence_role"], "visual_hypothesis")
        self.assertEqual(analysis["visual_hypotheses"][0]["status"], "hypothesis")
        self.assertNotIn("confirmed", str(analysis["visual_hypotheses"]).lower())
        botanist_context = run(self.fixture.botanist.build_context(self.fixture.context(), plant.id))
        self.assertEqual(botanist_context.recent_visual_analyses[0]["id"], analysis["id"])
        self.assertEqual(self.fixture.model_run_count(), 0)

    def test_visual_analysis_creates_plant_workspace_observation_without_merging_facts_and_hypotheses(self) -> None:
        plant = self.fixture.create_tomato_user_plant()
        media = self.fixture.create_media(plant.id)
        result = run(self.fixture.vision.analyze_attachment(self.fixture.context(), tool=self.fixture.vision_tool, media_attachment_id=media.id, user_plant_id=plant.id))

        observation = self.fixture.repo.get_observation(self.fixture.org.id, result.observation_id)
        self.assertIn(media.id, observation["images"])
        self.assertEqual(observation["observed_facts"][0]["evidence_role"], "visual_observation")
        self.assertEqual(observation["gaia_inferences"][0]["evidence_role"], "visual_hypothesis")
        self.assertNotEqual(observation["observed_facts"][0]["label"], observation["gaia_inferences"][0]["label"])

    def test_overclaiming_provider_output_fails_validation_and_does_not_persist_diagnosis(self) -> None:
        fixture = Phase6Fixture(vision_provider=FixtureVisionProvider(overclaim=True))
        try:
            plant = fixture.create_tomato_user_plant()
            media = fixture.create_media(plant.id)
            result = run(fixture.vision.analyze_attachment(fixture.context(), tool=fixture.vision_tool, media_attachment_id=media.id, user_plant_id=plant.id))
            analysis = fixture.repo.get_visual_analysis(fixture.org.id, result.visual_analysis.id)

            self.assertEqual(analysis["status"], "VALIDATION_FAILED")
            self.assertEqual(analysis["visual_observations"], [])
            self.assertEqual(analysis["visual_hypotheses"], [])
            self.assertIn("Rejected unsafe visual output", " ".join(analysis["safety_notes"]))
        finally:
            fixture.close()

    def test_validation_rejects_confirmed_diagnosis_language(self) -> None:
        with self.assertRaises(VisionValidationError):
            validate_visual_response([], [{"label": "early blight", "status": "confirmed", "rationale": "Confirmed early blight."}])

    def test_media_and_user_plant_are_tenant_scoped(self) -> None:
        plant = self.fixture.create_tomato_user_plant()
        media = self.fixture.create_media(plant.id)
        other_context = self.fixture.context(org=self.fixture.other_org, user=self.fixture.other_user, workspace=self.fixture.other_workspace)

        with self.assertRaises(PermissionError):
            run(
                self.fixture.vision.analyze_attachment(
                    other_context,
                    tool=self.fixture.vision_tool,
                    media_attachment_id=media.id,
                    user_plant_id=plant.id,
                )
            )
        with self.assertRaises(TenantAccessError):
            self.fixture.repo.create_user_plant(
                UserPlant(
                    organization_id=self.fixture.other_org.id,
                    workspace_id=self.fixture.other_workspace.id,
                    plant_entity_id=plant.plant_entity_id,
                    nickname="cross tenant",
                    location_id=self.fixture.location.id,
                )
            )

    def test_vision_calls_pass_tool_gateway_cost_firewall_and_no_paid_fallback(self) -> None:
        plant = self.fixture.create_tomato_user_plant()
        media = self.fixture.create_media(plant.id)
        run(self.fixture.vision.analyze_attachment(self.fixture.context(), tool=self.fixture.vision_tool, media_attachment_id=media.id, user_plant_id=plant.id))
        usage = self.fixture.ledger.organization_usage(self.fixture.org.id)

        self.assertTrue(any(event["provider_id"] == "fixture-vision-local" for event in usage))
        self.assertTrue(all(event["estimated_cost_usd"] == 0.0 for event in usage))
        self.assertNotIn("future-paid-provider", {event["provider_id"] for event in usage})

    def test_cached_vision_analysis_avoids_second_provider_call(self) -> None:
        plant = self.fixture.create_tomato_user_plant()
        media = self.fixture.create_media(plant.id)
        run(self.fixture.vision.analyze_attachment(self.fixture.context(), tool=self.fixture.vision_tool, media_attachment_id=media.id, user_plant_id=plant.id))
        run(self.fixture.vision.analyze_attachment(self.fixture.context(), tool=self.fixture.vision_tool, media_attachment_id=media.id, user_plant_id=plant.id))

        self.assertEqual(self.fixture.vision_provider.calls, 1)
        self.assertEqual(self.fixture.ledger.organization_usage(self.fixture.org.id)[-1]["status"], "cache_hit")

    def test_plantnet_fixture_is_optional_and_not_a_diagnosis(self) -> None:
        media = self.fixture.create_media()
        result = run(self.fixture.vision.analyze_attachment(self.fixture.context(), tool=self.fixture.plantnet_tool, media_attachment_id=media.id, persist_observation=False))

        analysis = self.fixture.repo.get_visual_analysis(self.fixture.org.id, result.visual_analysis.id)
        self.assertEqual(analysis["provider"], "plantnet")
        self.assertEqual(analysis["plant_candidates"][0]["common_name"], "tomato")
        self.assertIn("not a disease diagnosis", " ".join(analysis["safety_notes"]))

    def test_plantnet_adapter_normalizes_fixture_response_without_api_key_or_live_call(self) -> None:
        payload = {
            "query": {"project": "all"},
            "results": [
                {
                    "score": 0.81,
                    "species": {
                        "id": "solanum-lycopersicum",
                        "scientificNameWithoutAuthor": "Solanum lycopersicum",
                        "commonNames": ["tomato"],
                    },
                }
            ],
        }
        adapter = PlantNetAdapter()

        self.assertEqual(normalize_plantnet_identification(payload)[0]["scientific_name"], "Solanum lycopersicum")
        self.assertEqual(run(adapter.analyze(__import__("packages.vision", fromlist=["VisionRequest"]).VisionRequest(TINY_PNG_BASE64, "image/png", "identify"))).status, "UNAVAILABLE")
        self.assertEqual(adapter.fixture_response(payload).plant_candidates[0]["common_name"], "tomato")

    def test_remote_private_image_egress_can_be_denied_even_for_free_provider(self) -> None:
        media = self.fixture.create_media()
        result = run(
            self.fixture.vision.analyze_attachment(
                self.fixture.context(egress_policy=DataEgressPolicy.sovereign_default()),
                tool=self.fixture.plantnet_tool,
                media_attachment_id=media.id,
                persist_observation=False,
            )
        )

        analysis = self.fixture.repo.get_visual_analysis(self.fixture.org.id, result.visual_analysis.id)
        self.assertEqual(analysis["status"], "UNAVAILABLE")
        self.assertEqual(result.provider_result.denial_reason, "private_image_egress_denied")

    def test_provider_failure_persists_unavailable_analysis_without_breaking_workspace(self) -> None:
        fixture = Phase6Fixture(vision_provider=FixtureVisionProvider(unavailable=True))
        try:
            plant = fixture.create_tomato_user_plant()
            media = fixture.create_media(plant.id)
            result = run(fixture.vision.analyze_attachment(fixture.context(), tool=fixture.vision_tool, media_attachment_id=media.id, user_plant_id=plant.id))
            analysis = fixture.repo.get_visual_analysis(fixture.org.id, result.visual_analysis.id)

            self.assertEqual(analysis["status"], "PROVIDER_ERROR")
            self.assertEqual(analysis["visual_observations"], [])
            self.assertEqual(fixture.repo.list_observations(fixture.org.id, plant.id), [])
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
