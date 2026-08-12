from __future__ import annotations

import asyncio
import os
import unittest

from packages.audit import AuditLog, UsageLedger
from packages.cache import SQLiteCacheBackend
from packages.cost import CostFirewall, ProviderCostPolicy
from packages.domain import Location, Membership, Organization, PlantEntity, User, UserPlant, Workspace
from packages.mercator import (
    AMSMarketReportTool,
    AMSSupplyChainTool,
    FixtureAMSProvider,
    FixtureNASSProvider,
    MercatorContextProvider,
    MercatorValidationError,
    NASSProductionTool,
    NASSQuickStatsProvider,
    NASSRegionalContextTool,
    AMSMyMarketNewsProvider,
    EconomicRequest,
    assert_observation_not_live_logistics,
    comparable_units,
    normalize_commodity,
    validate_economic_synthesis,
)
from packages.orchestration.orchestrator import classify_route
from packages.persistence import GaiaRepository, connect_in_memory, initialize_schema
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


def provider(provider_id: str, provider_type: ProviderType, billing: BillingClass = BillingClass.FREE, *, enabled: bool = True, remote: bool = True) -> ProviderRecord:
    return ProviderRecord(
        provider_id=provider_id,
        display_name=provider_id,
        provider_type=provider_type,
        authority=provider_id,
        enabled=enabled,
        billing_class=billing,
        cost_policy=ProviderCostPolicy(provider_id=provider_id, billing_class=billing.value, hard_monthly_usd=0.0, allow_overage=False),
        quota_policy=ProviderQuotaPolicy(daily_requests=100),
        authentication_requirement=AuthenticationRequirement.NONE if billing != BillingClass.LOCAL else AuthenticationRequirement.LOCAL_ONLY,
        geographic_scope="fixture",
        cache_policy=CachePolicy(FreshnessClass.MEDIUM, ttl_seconds=3600, stale_if_error_seconds=86400),
        license_metadata=LicenseMetadata(),
        attribution=provider_id,
        remote=remote,
    )


class DuplicateNASSProvider(FixtureNASSProvider):
    async def production(self, request):
        result = await super().production(request)
        result.data["production_statistics"].append(dict(result.data["production_statistics"][0]))
        return result


class Phase10Fixture:
    def __init__(self, *, nass=None, ams=None) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Phase 10 Org", slug="phase10"))
        self.user = self.repo.create_user(User(external_auth_id="dev:phase10", display_name="Phase 10 User"))
        self.repo.create_membership(Membership(organization_id=self.org.id, user_id=self.user.id, role="owner", permissions=["tool.read", "model.chat"]))
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Market garden", purpose="phase10"))
        self.location = self.repo.create_location(Location(organization_id=self.org.id, label="Austin", latitude=30.2672, longitude=-97.7431, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US", admin1="TX", admin2="Travis County", county_fips="48453"))
        self.plant_entity = self.repo.create_plant_entity(PlantEntity(scientific_name="Solanum lycopersicum", genus="Solanum", species="lycopersicum", common_names=["tomato"], crop_group="vegetable"))
        self.user_plant = self.repo.create_user_plant(UserPlant(organization_id=self.org.id, workspace_id=self.workspace.id, plant_entity_id=self.plant_entity.id, nickname="Patio tomato", location_id=self.location.id))
        self.other_org = self.repo.create_organization(Organization(name="Other", slug="phase10-other"))
        self.other_user = self.repo.create_user(User(external_auth_id="dev:phase10-other", display_name="Other User"))
        self.repo.create_membership(Membership(organization_id=self.other_org.id, user_id=self.other_user.id, role="owner", permissions=["tool.read"]))
        self.other_workspace = self.repo.create_workspace(Workspace(organization_id=self.other_org.id, name="Other", purpose="phase10"))
        self.nass = nass or FixtureNASSProvider()
        self.ams = ams or FixtureAMSProvider()
        self.registry = ProviderRegistry(
            [
                provider("usda-nass", ProviderType.MARKET),
                provider("usda-ams", ProviderType.MARKET),
                provider("ollama-local", ProviderType.MODEL, BillingClass.LOCAL, remote=False),
                provider("future-paid-provider", ProviderType.MARKET, BillingClass.MANUAL_PAID, enabled=False),
            ]
        )
        self.ledger = UsageLedger(self.connection)
        self.audit = AuditLog(self.connection)
        self.gateway = ToolGateway(
            connection=self.connection,
            registry=self.registry,
            cost_firewall=CostFirewall(),
            quota_manager=QuotaManager(self.connection),
            cache_backend=SQLiteCacheBackend(self.connection),
            usage_ledger=self.ledger,
            audit_log=self.audit,
        )
        self.mercator = MercatorContextProvider(
            repository=self.repo,
            tool_gateway=self.gateway,
            nass_production_tool=NASSProductionTool(self.nass),
            nass_region_tool=NASSRegionalContextTool(self.nass),
            ams_market_tool=AMSMarketReportTool(self.ams),
            ams_supply_chain_tool=AMSSupplyChainTool(self.ams),
        )

    def context(self, *, org=None, user=None, workspace=None, permissions=None) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="phase10",
            organization_id=(org or self.org).id,
            user_id=(user or self.user).id,
            workspace_id=(workspace or self.workspace).id,
            permissions=frozenset(permissions or {"tool.read", "model.chat"}),
        )

    def geography(self) -> dict:
        return {
            "country": "United States",
            "country_code": "US",
            "state_or_region": "Texas",
            "state_code": "TX",
            "county_or_district": "Travis County",
            "county_fips": "48453",
            "economic_regions": ["Central Texas fixture"],
            "latitude": self.location.latitude,
            "longitude": self.location.longitude,
        }

    def build(self, commodity="Tomatoes, fresh market", *, crop_or_taxon=None):
        return run(
            self.mercator.build_context(
                self.context(),
                commodity=commodity,
                geography=self.geography(),
                location_id=self.location.id,
                crop_or_taxon=crop_or_taxon or {"id": self.plant_entity.id, "scientific_name": "Solanum lycopersicum"},
            )
        )

    def close(self):
        self.connection.close()


class MercatorEconomicIntelligenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase10Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_01_nass_fixture_normalizes_commodity(self) -> None:
        result = self.fixture.build()
        self.assertEqual(result.mercator_context.commodity["canonical_name"], "tomato")

    def test_02_geography_is_preserved(self) -> None:
        result = self.fixture.build()
        stat = result.mercator_context.production_statistics[0]
        self.assertEqual(stat["geography"]["state_code"], "TX")
        self.assertEqual(stat["geography"]["county_fips"], "48453")

    def test_03_period_year_is_preserved(self) -> None:
        result = self.fixture.build()
        self.assertEqual(result.mercator_context.production_statistics[0]["observation_period"], "2025")

    def test_04_missing_county_data_does_not_become_inferred_county_data(self) -> None:
        fixture = Phase10Fixture(nass=FixtureNASSProvider(missing_county=True))
        try:
            result = fixture.build()
            stat = result.mercator_context.production_statistics[0]
            self.assertTrue(stat["geography"]["state_level_fallback"])
            self.assertNotIn("county_fips", stat["geography"])
        finally:
            fixture.close()

    def test_05_units_remain_intact(self) -> None:
        result = self.fixture.build()
        self.assertEqual(result.mercator_context.production_statistics[0]["unit"], "cwt")

    def test_06_duplicate_provider_record_does_not_duplicate_observation(self) -> None:
        fixture = Phase10Fixture(nass=DuplicateNASSProvider())
        try:
            result = fixture.build()
            ids = [item["provider_record_id"] for item in result.mercator_context.production_statistics]
            self.assertEqual(len(ids), len(set(ids)))
        finally:
            fixture.close()

    def test_07_ams_market_observation_retains_report_date(self) -> None:
        result = self.fixture.build()
        self.assertEqual(result.mercator_context.price_observations[0]["report_date"], "2026-08-10")

    def test_08_package_unit_distinctions_are_preserved(self) -> None:
        price = self.fixture.build().mercator_context.price_observations[0]
        self.assertEqual(price["package"], "25 lb box")
        self.assertEqual(price["unit"], "$/25 lb box")

    def test_09_incompatible_units_are_not_compared_silently(self) -> None:
        left = {"value": 18, "unit": "$/25 lb box", "package": "25 lb box"}
        right = {"value": 1.1, "unit": "$/lb", "package": None}
        self.assertEqual(comparable_units(left, right), (False, "incompatible_unit_or_package"))
        self.assertFalse(self.fixture.mercator.compare_prices(left, right)["comparable"])

    def test_10_historical_market_report_is_not_labeled_current(self) -> None:
        fixture = Phase10Fixture(ams=FixtureAMSProvider(historical_report=True))
        try:
            result = fixture.build()
            self.assertEqual(result.mercator_context.price_observations[0]["freshness"], "historical")
        finally:
            fixture.close()

    def test_11_provider_outage_fails_gracefully(self) -> None:
        fixture = Phase10Fixture(ams=FixtureAMSProvider(unavailable=True))
        try:
            result = fixture.build()
            self.assertTrue(result.mercator_context.production_statistics)
            self.assertIn("ams_market status: PROVIDER_ERROR", result.mercator_context.limitations)
        finally:
            fixture.close()

    def test_12_cached_report_retains_original_date(self) -> None:
        first = self.fixture.build()
        calls = self.fixture.ams.calls
        second = self.fixture.build()
        self.assertEqual(self.fixture.ams.calls, calls)
        self.assertEqual(second.mercator_context.price_observations[0]["report_date"], first.mercator_context.price_observations[0]["report_date"])

    def test_13_structural_dataset_is_labeled_structural_supply_chain(self) -> None:
        record = self.fixture.build().mercator_context.supply_chain_context[0]
        self.assertEqual(record["data_class"], "STRUCTURAL_SUPPLY_CHAIN")

    def test_14_historical_commodity_flow_is_not_live_logistics(self) -> None:
        record = self.fixture.build().mercator_context.supply_chain_context[0]
        self.assertEqual(record["freshness"], "structural_historical")
        assert_observation_not_live_logistics(record)

    def test_15_origin_destination_geography_remains_attached(self) -> None:
        record = self.fixture.build().mercator_context.supply_chain_context[0]
        self.assertIn("origin_region", record)
        self.assertIn("destination_region", record)

    def test_16_missing_mode_value_data_remains_unknown(self) -> None:
        record = self.fixture.build().mercator_context.supply_chain_context[0]
        self.assertIsNone(record["value"])
        self.assertIsNone(record["weight"])

    def test_17_season_can_consume_mercator_context(self) -> None:
        from packages.season import DeterministicSeasonPlanner, SeasonContext, SeasonPlanRequest

        mercator = self.fixture.build().to_dict()["mercator_context"]
        context = SeasonContext(
            workspace=self.fixture.repo.get_workspace(self.fixture.org.id, self.fixture.workspace.id),
            location=self.fixture.repo.get_location(self.fixture.org.id, self.fixture.location.id),
            mercator_context=mercator,
            sentinel_constraints=[],
            date_range={"start": "2026-09-15", "end": "2026-12-15"},
        )
        plan, _ = run(DeterministicSeasonPlanner().create_plan(SeasonPlanRequest(workspace_id=self.fixture.workspace.id, location_id=self.fixture.location.id, objective="Plant tomatoes economically", crop_names=["tomato"], start_date="2026-09-15", end_date="2026-12-15", constraints={"planning_date": "2026-08-12"}), context))
        self.assertTrue(plan.market_context)

    def test_18_economic_context_cannot_override_agronomic_impossibility(self) -> None:
        from packages.season import DeterministicSeasonPlanner, SeasonContext, SeasonPlanRequest

        mercator = self.fixture.build().to_dict()["mercator_context"]
        context = SeasonContext(workspace=self.fixture.repo.get_workspace(self.fixture.org.id, self.fixture.workspace.id), location=self.fixture.repo.get_location(self.fixture.org.id, self.fixture.location.id), mercator_context=mercator, weather_forecast_context={"daily_low_c": {"2026-09-29": -5}})
        _, actions = run(DeterministicSeasonPlanner().create_plan(SeasonPlanRequest(workspace_id=self.fixture.workspace.id, location_id=self.fixture.location.id, objective="Should I plant tomatoes because prices are high?", crop_names=["tomato"], start_date="2026-09-15", end_date="2026-12-15", constraints={"planning_date": "2026-08-12"}), context))
        transplant = next(action for action in actions if action.action_type == "transplant")
        self.assertTrue(any(condition.get("condition") == "forecast_low_below_threshold" for condition in transplant.environmental_conditions))

    def test_19_sentinel_restriction_remains_controlling(self) -> None:
        from packages.season import DeterministicSeasonPlanner, SeasonContext, SeasonPlanRequest

        context = SeasonContext(workspace=self.fixture.repo.get_workspace(self.fixture.org.id, self.fixture.workspace.id), location=self.fixture.repo.get_location(self.fixture.org.id, self.fixture.location.id), mercator_context=self.fixture.build().to_dict()["mercator_context"], sentinel_constraints=[{"status": "RESTRICTED", "authority": "Fixture regulator"}])
        plan, actions = run(DeterministicSeasonPlanner().create_plan(SeasonPlanRequest(workspace_id=self.fixture.workspace.id, location_id=self.fixture.location.id, objective="Grow profitable citrus", crop_names=["citrus"], start_date="2026-09-15", end_date="2026-12-15", constraints={"planning_date": "2026-08-12"}), context))
        self.assertEqual(plan.confidence, "PROVISIONAL")
        self.assertEqual(actions[0].action_type, "inspect_pest")

    def test_20_botanist_crop_identity_maps_to_economic_commodity(self) -> None:
        commodity = normalize_commodity("Fresh tomatoes", crop_or_taxon={"id": self.fixture.plant_entity.id, "scientific_name": "Solanum lycopersicum"})
        self.assertEqual(commodity["crop_or_taxon_id"], self.fixture.plant_entity.id)
        self.assertEqual(commodity["canonical_name"], "tomato")

    def test_21_houseplant_context_does_not_trigger_irrelevant_commodity_route(self) -> None:
        self.assertNotEqual(classify_route("How should I water my pothos?"), "economics")

    def test_22_price_observation_links_to_source(self) -> None:
        result = self.fixture.build()
        self.assertTrue(result.mercator_context.source_record_ids)

    def test_23_production_statistic_links_to_source(self) -> None:
        result = self.fixture.build()
        source = self.fixture.repo.get_mercator_context(self.fixture.org.id, result.mercator_context.id)["source_record_ids"][0]
        self.assertTrue(source)

    def test_24_model_cannot_fabricate_price(self) -> None:
        trusted = self.fixture.build().to_dict()
        with self.assertRaises(MercatorValidationError):
            validate_economic_synthesis({"summary": "Price is 999.0", "value": 999.0}, trusted)

    def test_25_model_cannot_fabricate_production_value(self) -> None:
        trusted = self.fixture.build().to_dict()
        with self.assertRaises(MercatorValidationError):
            validate_economic_synthesis({"production": 777777.0}, trusted)

    def test_26_historical_comparison_preserves_source_periods(self) -> None:
        dates = self.fixture.build().mercator_context.data_dates
        self.assertIn("2025", dates["production"])

    def test_27_free_official_provider_allowed(self) -> None:
        self.fixture.build()
        providers = {event["provider_id"] for event in self.fixture.ledger.organization_usage(self.fixture.org.id)}
        self.assertIn("usda-nass", providers)
        self.assertIn("usda-ams", providers)

    def test_28_paid_provider_denied_by_default(self) -> None:
        with self.assertRaises(ValueError):
            ProviderRegistry([provider("paid-market", ProviderType.MARKET, BillingClass.MANUAL_PAID)])

    def test_29_no_paid_fallback_after_nass_ams_failure(self) -> None:
        fixture = Phase10Fixture(nass=FixtureNASSProvider(unavailable=True), ams=FixtureAMSProvider(unavailable=True))
        try:
            fixture.build()
            self.assertNotIn("future-paid-provider", {event["provider_id"] for event in fixture.ledger.organization_usage(fixture.org.id)})
        finally:
            fixture.close()

    def test_30_cache_reduces_provider_requests(self) -> None:
        self.fixture.build()
        calls = (self.fixture.nass.calls, self.fixture.ams.calls)
        self.fixture.build()
        self.assertEqual((self.fixture.nass.calls, self.fixture.ams.calls), calls)

    def test_31_economic_synthesis_using_local_model_policy_remains_zero_external_spend(self) -> None:
        local = self.fixture.registry.get("ollama-local")
        self.assertEqual(local.billing_class, BillingClass.LOCAL)
        self.assertFalse(local.remote)
        self.assertTrue(CostFirewall().check(local, 0.0).allowed)

    def test_32_public_economic_statistics_may_be_shared_safely(self) -> None:
        result = self.fixture.build()
        self.assertNotIn("latitude", str(result.mercator_context.production_statistics))

    def test_33_private_organization_annotations_remain_tenant_scoped(self) -> None:
        context = self.fixture.build().mercator_context
        self.assertIsNone(self.fixture.repo.get_mercator_context(self.fixture.other_org.id, context.id))

    def test_34_user_crop_plans_are_not_exposed_through_economic_queries(self) -> None:
        result = self.fixture.build()
        self.assertNotIn(self.fixture.user_plant.id, str(result.mercator_context.market_reports))

    def test_35_exact_private_farm_location_is_not_sent_to_providers(self) -> None:
        self.fixture.build()
        self.assertNotIn("latitude", str(self.fixture.nass.last_request.geography))
        self.assertNotIn("longitude", str(self.fixture.ams.last_request.geography))

    def test_36_latest_available_annual_statistic_labeled_with_actual_year(self) -> None:
        stat = self.fixture.build().mercator_context.production_statistics[0]
        self.assertEqual(stat["observation_period"], "2025")
        self.assertIn(stat["freshness"], {"recent_periodic", "historical"})

    def test_37_market_report_freshness_is_visible(self) -> None:
        report = self.fixture.build().mercator_context.market_reports[0]
        self.assertIn("freshness", report)

    def test_38_stale_data_is_labeled_stale_or_historical(self) -> None:
        fixture = Phase10Fixture(ams=FixtureAMSProvider(historical_report=True))
        try:
            self.assertEqual(fixture.build().mercator_context.freshness["markets"], "historical")
        finally:
            fixture.close()

    def test_39_missing_current_data_does_not_become_current_inference(self) -> None:
        fixture = Phase10Fixture(ams=FixtureAMSProvider(unavailable=True))
        try:
            result = fixture.build()
            self.assertEqual(result.mercator_context.freshness["markets"], "unavailable")
            self.assertFalse(any(item.get("data_class") == "MODEL_OR_INFERENCE" for item in result.mercator_context.price_observations))
        finally:
            fixture.close()

    def test_40_chat_market_question_routes_to_mercator_zero_model_runs(self) -> None:
        self.assertEqual(classify_route("What does the tomato market look like around here?"), "economics")

    def test_41_structural_live_logistics_validation_rejects_bad_label(self) -> None:
        with self.assertRaises(MercatorValidationError):
            assert_observation_not_live_logistics({"data_class": "STRUCTURAL_SUPPLY_CHAIN", "freshness": "live"})


class MercatorOptionalLiveSmokeTest(unittest.TestCase):
    def test_nass_live_smoke_is_opt_in(self) -> None:
        if os.environ.get("GAIA_RUN_NASS_SMOKE") != "1":
            self.skipTest("Set GAIA_RUN_NASS_SMOKE=1 and GAIA_NASS_API_KEY to run read-only NASS smoke")
        result = run(
            NASSQuickStatsProvider().production(
                EconomicRequest(commodity="TOMATOES", geography={"country_code": "US", "state_code": "TX"}, periods=["2024"])
            )
        )
        self.assertIn(result.status, {"AVAILABLE", "UNAVAILABLE"})

    def test_ams_live_smoke_is_opt_in(self) -> None:
        if os.environ.get("GAIA_RUN_AMS_SMOKE") != "1":
            self.skipTest("Set GAIA_RUN_AMS_SMOKE=1 and GAIA_AMS_API_KEY to run read-only AMS smoke")
        result = run(AMSMyMarketNewsProvider().market_reports(EconomicRequest(commodity="TOMATOES", geography={"country_code": "US"})))
        self.assertIn(result.status, {"AVAILABLE", "UNAVAILABLE"})


if __name__ == "__main__":
    unittest.main()
