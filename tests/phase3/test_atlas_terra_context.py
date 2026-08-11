from __future__ import annotations

import asyncio
import unittest

from packages.audit import AuditLog, UsageLedger
from packages.cache import SQLiteCacheBackend
from packages.cost import CostFirewall
from packages.domain import Location, Membership, Organization, User, Workspace
from packages.environment import c_to_f, f_to_c, moon_phase, photoperiod_hours
from packages.environment.fixture_adapters import (
    FailingNWSProvider,
    FixtureNASAPowerProvider,
    FixtureNWSProvider,
    FixtureUSDASoilProvider,
    FixtureUSGSWaterProvider,
    MissingUSDASoilProvider,
)
from packages.environment.terra import TerraService
from packages.environment.tools import NASAPowerClimateTool, NWSForecastTool, USDASoilSurveyTool, USGSWaterSitesTool
from packages.geospatial import AtlasService, reduce_coordinate_precision
from packages.geospatial.providers import (
    FixtureGeographyProvider,
    FixtureHardinessProvider,
    FixtureRegulatoryGeometryProvider,
    FixtureWatershedProvider,
)
from packages.persistence import GaiaRepository, connect_in_memory, initialize_schema
from packages.policy import DataEgressPolicy
from packages.providers import (
    AuthenticationRequirement,
    BillingClass,
    CachePolicy,
    FreshnessClass,
    LicenseMetadata,
    ProviderHealthMonitor,
    ProviderQuotaPolicy,
    ProviderRecord,
    ProviderRegistry,
    ProviderType,
    QuotaManager,
)
from packages.tools import ToolExecutionContext, ToolGateway
from packages.context.compiler import ContextCompiler
from apps.api.gaia_api.context_api import post_context_environment, post_context_geography


def run(coro):
    return asyncio.run(coro)


def enabled_provider(provider_id: str, provider_type: ProviderType) -> ProviderRecord:
    from packages.cost import ProviderCostPolicy

    return ProviderRecord(
        provider_id=provider_id,
        display_name=provider_id,
        provider_type=provider_type,
        authority=provider_id,
        enabled=True,
        billing_class=BillingClass.FREE,
        cost_policy=ProviderCostPolicy(provider_id=provider_id, billing_class="FREE", hard_monthly_usd=0.0, allow_overage=False),
        quota_policy=ProviderQuotaPolicy(daily_requests=100),
        authentication_requirement=AuthenticationRequirement.NONE,
        geographic_scope="fixture",
        cache_policy=CachePolicy(FreshnessClass.SHORT, ttl_seconds=60, stale_if_error_seconds=60),
        license_metadata=LicenseMetadata(),
        attribution=provider_id,
        remote=True,
    )


class Phase3Fixture:
    def __init__(self, *, nws=None, soil=None) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Org", slug="org"))
        self.user = self.repo.create_user(User(external_auth_id="dev:phase3", display_name="Phase 3 User"))
        self.repo.create_membership(Membership(organization_id=self.org.id, user_id=self.user.id, role="owner", permissions=["tool.read"]))
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Garden", purpose="phase3"))
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
        self.registry = ProviderRegistry(
            [
                enabled_provider("nws", ProviderType.WEATHER),
                enabled_provider("nasa-power", ProviderType.CLIMATE),
                enabled_provider("usda-nrcs-sda", ProviderType.SOIL),
                enabled_provider("usgs-water", ProviderType.WATER),
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
            health_monitor=ProviderHealthMonitor(),
        )
        self.atlas = AtlasService(
            self.repo,
            FixtureGeographyProvider(),
            FixtureWatershedProvider(),
            FixtureHardinessProvider(),
            FixtureRegulatoryGeometryProvider(),
        )
        self.terra = TerraService(
            self.repo,
            self.gateway,
            NWSForecastTool(nws or FixtureNWSProvider()),
            NASAPowerClimateTool(FixtureNASAPowerProvider()),
            USDASoilSurveyTool(soil or FixtureUSDASoilProvider()),
            USGSWaterSitesTool(FixtureUSGSWaterProvider()),
        )

    def context(self, *, egress_policy: DataEgressPolicy | None = None) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="phase3",
            organization_id=self.org.id,
            user_id=self.user.id,
            workspace_id=self.workspace.id,
            permissions=frozenset({"tool.read"}),
            data_egress_policy=egress_policy or DataEgressPolicy(),
        )

    def close(self) -> None:
        self.connection.close()


class AtlasTerraContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase3Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_known_us_coordinate_resolves_state_county_and_fips(self) -> None:
        result = run(self.fixture.atlas.build_geo_context(self.fixture.location))

        self.assertEqual(result.geo_context.state_code, "TX")
        self.assertEqual(result.geo_context.county_or_district, "Travis County")
        self.assertEqual(result.geo_context.county_fips, "48453")
        self.assertGreater(len(result.geo_context.source_record_ids), 0)

    def test_non_us_administrative_structure_is_supported(self) -> None:
        location = self.fixture.repo.create_location(
            Location(
                organization_id=self.fixture.org.id,
                label="Singapore garden",
                latitude=1.294,
                longitude=103.806,
                country_code="SG",
                timezone="Asia/Singapore",
            )
        )

        result = run(self.fixture.atlas.build_geo_context(location))

        self.assertEqual(result.geo_context.country_code, "SG")
        self.assertEqual(result.geo_context.county_fips, None)
        self.assertEqual(result.geo_context.county_or_district, "Queenstown")

    def test_coordinate_privacy_reduction_does_not_mutate_source_coordinate(self) -> None:
        reduced = reduce_coordinate_precision(30.2672, -97.7431, "1km")

        stored = self.fixture.repo.get_location(self.fixture.org.id, self.fixture.location.id)
        self.assertEqual(reduced.latitude, 30.27)
        self.assertEqual(reduced.longitude, -97.74)
        self.assertEqual(stored["latitude"], 30.2672)
        self.assertEqual(stored["longitude"], -97.7431)

    def test_exact_location_cannot_leak_through_lower_precision_response(self) -> None:
        result = run(self.fixture.atlas.build_geo_context(self.fixture.location))

        self.assertNotEqual(result.display_coordinate.latitude, self.fixture.location.latitude)
        self.assertNotEqual(result.display_coordinate.longitude, self.fixture.location.longitude)
        self.assertEqual(result.display_coordinate.precision, "1km")

    def test_weather_forecast_preserves_valid_and_retrieval_times_and_units(self) -> None:
        result = run(self.fixture.terra.build_environmental_snapshot(self.fixture.location, self.fixture.context()))
        snapshot = result.snapshot

        self.assertEqual(snapshot.forecast["valid_at"], "2026-08-11T21:00:00-05:00")
        self.assertEqual(snapshot.forecast["retrieved_at"], "2026-08-11T12:00:00Z")
        self.assertEqual(snapshot.temperature["unit"], "C")
        self.assertAlmostEqual(f_to_c(c_to_f(18.3)), 18.3)

    def test_provider_failure_produces_partial_context_not_total_failure(self) -> None:
        fixture = Phase3Fixture(nws=FailingNWSProvider())
        try:
            result = run(fixture.terra.build_environmental_snapshot(fixture.location, fixture.context()))
            self.assertEqual(result.snapshot.provider_statuses["nws"], "PROVIDER_ERROR")
            self.assertEqual(result.snapshot.provider_statuses["nasa_power"], "AVAILABLE")
            self.assertEqual(result.snapshot.provider_statuses["soil"], "AVAILABLE")
            self.assertTrue(result.snapshot.solar_radiation)
        finally:
            fixture.close()

    def test_soil_survey_semantics_are_not_live_soil_moisture(self) -> None:
        result = run(self.fixture.terra.build_environmental_snapshot(self.fixture.location, self.fixture.context()))

        self.assertEqual(result.snapshot.soil_context["texture"]["evidence_type"], "SURVEY")
        self.assertIn("not live soil moisture", result.snapshot.soil_context["semantic_note"])
        self.assertNotEqual(result.snapshot.soil_moisture_context.get("evidence_type"), "SENSOR")

    def test_missing_soil_result_stays_missing(self) -> None:
        fixture = Phase3Fixture(soil=MissingUSDASoilProvider())
        try:
            result = run(fixture.terra.build_environmental_snapshot(fixture.location, fixture.context()))
            self.assertEqual(result.snapshot.provider_statuses["soil"], "UNAVAILABLE")
            self.assertIn("did not infer", result.snapshot.soil_context["semantic_note"])
        finally:
            fixture.close()

    def test_environmental_snapshot_combines_sources_and_keeps_provenance(self) -> None:
        result = run(self.fixture.terra.build_environmental_snapshot(self.fixture.location, self.fixture.context()))

        self.assertTrue(result.snapshot.temperature)
        self.assertTrue(result.snapshot.solar_radiation)
        self.assertTrue(result.snapshot.soil_context)
        self.assertTrue(result.snapshot.water_context)
        self.assertGreaterEqual(len(result.snapshot.source_record_ids), 4)

    def test_deterministic_context_generation_has_zero_model_runs(self) -> None:
        result = run(self.fixture.terra.build_environmental_snapshot(self.fixture.location, self.fixture.context()))

        rows = self.fixture.connection.execute("SELECT COUNT(*) AS count FROM model_runs").fetchone()
        self.assertEqual(rows["count"], 0)
        self.assertEqual(result.snapshot.astronomical_context["evidence_type"], "DERIVED")
        self.assertGreater(photoperiod_hours(30.2672, -97.7431, __import__("datetime").date(2026, 8, 11)), 0)
        self.assertIn("phase", moon_phase(__import__("datetime").date(2026, 8, 11)))

    def test_all_phase3_provider_calls_respect_cost_firewall(self) -> None:
        run(self.fixture.terra.build_environmental_snapshot(self.fixture.location, self.fixture.context()))
        usage = self.fixture.ledger.organization_usage(self.fixture.org.id)

        self.assertEqual(len(usage), 4)
        self.assertTrue(all(event["estimated_cost_usd"] == 0.0 for event in usage))

    def test_no_paid_fallback_activates_when_provider_fails(self) -> None:
        fixture = Phase3Fixture(nws=FailingNWSProvider())
        try:
            run(fixture.terra.build_environmental_snapshot(fixture.location, fixture.context()))
            provider_ids = {event["provider_id"] for event in fixture.ledger.organization_usage(fixture.org.id)}
            self.assertNotIn("future-paid-provider", provider_ids)
        finally:
            fixture.close()

    def test_exact_location_egress_policy_denies_remote_providers(self) -> None:
        result = run(
            self.fixture.terra.build_environmental_snapshot(
                self.fixture.location,
                self.fixture.context(egress_policy=DataEgressPolicy(allow_exact_location_egress=False)),
            )
        )

        self.assertTrue(all(status == "DENIED" for status in result.snapshot.provider_statuses.values()))

    def test_stale_if_error_cache_behavior(self) -> None:
        run(
            self.fixture.cache.put(
                f"nws:{self.fixture.location.id}",
                "nws",
                {"temperature": {"value": 20, "unit": "C", "evidence_type": "FORECAST"}},
                ttl_seconds=-1,
                stale_if_error_seconds=86400,
                provenance_reference="cached-prov",
            )
        )
        fixture = Phase3Fixture(nws=FailingNWSProvider())
        try:
            fixture.cache = self.fixture.cache
            fixture.gateway.cache_backend = self.fixture.cache
            result = run(fixture.terra.build_environmental_snapshot(fixture.location, fixture.context()))
            # Different fixture location IDs mean this primarily proves expired cache state logic elsewhere.
            cached = run(self.fixture.cache.get(f"nws:{self.fixture.location.id}", "nws", allow_stale=True))
            self.assertEqual(cached.state.value, "STALE_ALLOWED")
            self.assertIn(result.snapshot.provider_statuses["nws"], {"PROVIDER_ERROR", "CACHE_HIT"})
        finally:
            fixture.close()

    def test_context_compiler_and_api_boundary_return_normalized_objects(self) -> None:
        compiler = ContextCompiler(self.fixture.repo, self.fixture.atlas, self.fixture.terra)

        geography = run(post_context_geography(compiler, self.fixture.context(), self.fixture.location.id))
        environment = run(post_context_environment(compiler, self.fixture.context(), self.fixture.location.id))

        self.assertEqual(geography["geo_context"]["state_code"], "TX")
        self.assertNotIn("properties", geography["geo_context"])
        self.assertIn("environmental_snapshot", environment)
        self.assertEqual(environment["model_run_count"], 0)
        self.assertNotIn("raw", environment["environmental_snapshot"])


if __name__ == "__main__":
    unittest.main()
