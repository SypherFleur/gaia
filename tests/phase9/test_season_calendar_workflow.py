from __future__ import annotations

import asyncio
import unittest

from packages.audit import AuditLog, UsageLedger
from packages.cache import SQLiteCacheBackend
from packages.calendar_gateway import CalendarCreateEventTool, CalendarWorkflowService, FixtureCalendarProvider
from packages.cost import CostFirewall, ProviderCostPolicy
from packages.domain import CalendarBinding, Location, Membership, Organization, Outcome, PlantEntity, SourceRecord, User, UserPlant, Workspace
from packages.model_gateway import FixtureGuidanceModelProvider, ModelGateway
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
from packages.season import SeasonContext, SeasonContextProvider, SeasonPlanRequest, SeasonService, horizon_basis, season_gdd_summary
from packages.tools import ToolExecutionContext, ToolGateway


def run(coro):
    return asyncio.run(coro)


def provider(
    provider_id: str,
    provider_type: ProviderType,
    billing: BillingClass = BillingClass.FREE,
    *,
    enabled: bool = True,
    remote: bool = True,
    auth: AuthenticationRequirement | None = None,
) -> ProviderRecord:
    return ProviderRecord(
        provider_id=provider_id,
        display_name=provider_id,
        provider_type=provider_type,
        authority=provider_id,
        enabled=enabled,
        billing_class=billing,
        cost_policy=ProviderCostPolicy(provider_id=provider_id, billing_class=billing.value, hard_monthly_usd=0.0, allow_overage=False),
        quota_policy=ProviderQuotaPolicy(daily_requests=100),
        authentication_requirement=auth or (AuthenticationRequirement.NONE if billing != BillingClass.LOCAL else AuthenticationRequirement.LOCAL_ONLY),
        geographic_scope="fixture",
        cache_policy=CachePolicy(FreshnessClass.STATIC, ttl_seconds=3600),
        license_metadata=LicenseMetadata(),
        attribution=provider_id,
        remote=remote,
    )


class Phase9Fixture:
    def __init__(self, *, calendar_unavailable: bool = False) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Phase 9 Org", slug="phase9"))
        self.user = self.repo.create_user(User(external_auth_id="dev:phase9", display_name="Phase 9 User"))
        self.repo.create_membership(Membership(organization_id=self.org.id, user_id=self.user.id, role="owner", permissions=["tool.read", "calendar.read", "calendar.create", "model.chat"]))
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Fall garden", purpose="season"))
        self.location = self.repo.create_location(Location(organization_id=self.org.id, label="Austin", latitude=30.2672, longitude=-97.7431, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/Chicago", country_code="US"))
        self.plant_entity = self.repo.create_plant_entity(PlantEntity(scientific_name="Solanum lycopersicum", genus="Solanum", species="lycopersicum"))
        self.user_plant = self.repo.create_user_plant(UserPlant(organization_id=self.org.id, workspace_id=self.workspace.id, plant_entity_id=self.plant_entity.id, nickname="Patio tomato", cultivar=None, location_id=self.location.id))
        self.source = self.repo.create_source_record(SourceRecord(organization_id=self.org.id, provider="fixture-season", source_type="climate", title="Fixture climate normals"))
        self.calendar_provider = FixtureCalendarProvider(unavailable=calendar_unavailable)
        self.registry = ProviderRegistry(
            [
                provider("fixture-calendar", ProviderType.CALENDAR, BillingClass.LOCAL, remote=False),
                provider("ollama-local", ProviderType.MODEL, BillingClass.LOCAL, remote=False),
                provider("google-calendar", ProviderType.CALENDAR, BillingClass.FREE, enabled=False, auth=AuthenticationRequirement.OAUTH),
                provider("future-paid-provider", ProviderType.CALENDAR, BillingClass.MANUAL_PAID, enabled=False),
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
        self.calendar = CalendarWorkflowService(
            repository=self.repo,
            tool_gateway=self.gateway,
            create_tool=CalendarCreateEventTool(self.calendar_provider, "fixture-calendar"),
        )
        self.model_gateway = ModelGateway(
            connection=self.connection,
            registry=self.registry,
            providers={"ollama-local": FixtureGuidanceModelProvider()},
            cost_firewall=CostFirewall(),
            usage_ledger=self.ledger,
            audit_log=self.audit,
        )
        self.season = SeasonService(repository=self.repo, model_gateway=self.model_gateway)
        self.calendar_binding = self.repo.create_calendar_binding(
            CalendarBinding(
                organization_id=self.org.id,
                user_id=self.user.id,
                provider="fixture-calendar",
                external_calendar_id="fixture-primary",
                encrypted_credential_reference="secret-calendar-token",
                credential_reference="fixture-credential",
                scopes=["calendar.read", "calendar.create"],
            )
        )
        self.other_org = self.repo.create_organization(Organization(name="Other", slug="phase9-other"))
        self.other_user = self.repo.create_user(User(external_auth_id="dev:phase9-other", display_name="Other User"))
        self.repo.create_membership(Membership(organization_id=self.other_org.id, user_id=self.other_user.id, role="owner", permissions=["tool.read", "calendar.read", "calendar.create"]))
        self.other_workspace = self.repo.create_workspace(Workspace(organization_id=self.other_org.id, name="Other", purpose="season"))

    def context(self, *, permissions=None, org=None, user=None, workspace=None) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="phase9",
            organization_id=(org or self.org).id,
            user_id=(user or self.user).id,
            workspace_id=(workspace or self.workspace).id,
            permissions=frozenset(permissions or {"tool.read", "calendar.read", "calendar.create", "model.chat"}),
        )

    def season_context(self, *, forecast=None, sentinel=None, scholar=None, latitude=None, luna=True) -> SeasonContext:
        location = self.repo.get_location(self.org.id, self.location.id)
        if latitude is not None:
            location = {**location, "latitude": latitude}
        return SeasonContext(
            workspace=self.repo.get_workspace(self.org.id, self.workspace.id),
            location=location,
            geo_context={"source_record_ids": [self.source.id], "country_code": "US", "state_code": "TX"},
            environmental_snapshot={
                "source_record_ids": [self.source.id],
                "soil_moisture_context": {"evidence_type": "MODELED", "semantic_note": "regional modeled context, not sensor"},
            },
            weather_forecast_context=forecast or {},
            user_plants=[self.repo.get_user_plant(self.org.id, self.user_plant.id)],
            plant_profiles=[],
            sentinel_constraints=sentinel or [],
            scholar_evidence=scholar or [],
            date_range={"start": "2026-09-15", "end": "2026-12-15"},
            timezone="America/Chicago",
            luna_context={"phase": "waxing crescent", "evidence_status": "Experimental", "influence_on_plan": "None"} if luna else {},
        )

    def request(self, **overrides) -> SeasonPlanRequest:
        params = {
            "workspace_id": self.workspace.id,
            "location_id": self.location.id,
            "objective": "Plan tomatoes, peppers and collards for my fall garden.",
            "crop_names": ["tomato", "pepper", "collard"],
            "start_date": "2026-09-15",
            "end_date": "2026-12-15",
            "constraints": {"planning_date": "2026-08-11"},
            "timezone": "America/Chicago",
        }
        params.update(overrides)
        return SeasonPlanRequest(**params)

    def create_plan(self, request=None, context=None):
        return run(self.season.create_plan(self.context(), request or self.request(), context or self.season_context()))

    def close(self) -> None:
        self.connection.close()


class Phase9SeasonCalendarTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase9Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_01_crop_plan_creates_structured_actions(self) -> None:
        plan, actions, _ = self.fixture.create_plan()
        self.assertEqual(plan.objective, "Plan tomatoes, peppers and collards for my fall garden.")
        self.assertGreaterEqual(len(actions), 15)

    def test_02_multiple_crops_share_one_season_plan(self) -> None:
        plan, actions, _ = self.fixture.create_plan()
        crops = {action.plant_or_crop_id for action in actions}
        self.assertEqual(plan.id, actions[0].season_plan_id)
        self.assertTrue({"tomato", "pepper", "collard"}.issubset(crops))

    def test_03_long_range_plan_uses_climate_not_forecast(self) -> None:
        request = self.fixture.request(start_date="2027-02-15", end_date="2027-05-01")
        plan, _, _ = self.fixture.create_plan(request=request)
        self.assertEqual(plan.climate_basis["timing_basis"], "climate_normals_historical_distribution")
        self.assertTrue(plan.climate_basis["not_weather_forecast"])

    def test_04_near_term_task_uses_forecast_basis(self) -> None:
        request = self.fixture.request(start_date="2026-08-16", end_date="2026-09-15")
        plan, _, _ = self.fixture.create_plan(request=request)
        self.assertTrue(plan.forecast_basis["forecast_used"])

    def test_05_southern_hemisphere_dates_behave_without_spring_hardcode(self) -> None:
        plan, _, _ = self.fixture.create_plan(context=self.fixture.season_context(latitude=-33.8))
        self.assertEqual(plan.planning_basis["hemisphere"], "southern")
        self.assertEqual(plan.start_date, "2026-09-15")

    def test_06_user_unavailable_dates_change_preferred_timing(self) -> None:
        request = self.fixture.request(constraints={"planning_date": "2026-08-11", "vacation_dates": [{"start": "2026-09-29", "end": "2026-10-05"}]})
        _, actions, _ = self.fixture.create_plan(request=request)
        self.assertFalse(any("2026-09-29" <= action.preferred_at[:10] <= "2026-10-05" for action in actions))

    def test_07_unknown_cultivar_does_not_invent_thresholds(self) -> None:
        request = self.fixture.request(constraints={"planning_date": "2026-08-11", "cultivar_unknown": True})
        plan, actions, _ = self.fixture.create_plan(request=request)
        self.assertIn(plan.confidence, {"MODERATE", "LOW"})
        self.assertFalse(any("Cherokee Purple threshold" in action.instructions for action in actions))

    def test_08_frost_risk_can_shift_or_condition_action(self) -> None:
        forecast = {"daily_low_c": {"2026-09-29": 5}}
        _, actions, _ = self.fixture.create_plan(context=self.fixture.season_context(forecast=forecast))
        transplant = next(action for action in actions if action.action_type == "transplant" and action.plant_or_crop_id == "tomato")
        self.assertTrue(any(condition.get("condition") == "forecast_low_below_threshold" for condition in transplant.environmental_conditions))

    def test_09_heavy_rain_triggers_proposed_revision(self) -> None:
        plan, actions, _ = self.fixture.create_plan()
        rain_day = actions[1].preferred_at[:10]
        revision = run(self.fixture.season.revise_plan(self.fixture.context(), plan.id, self.fixture.season_context(forecast={"heavy_rain_dates": [rain_day]})))
        self.assertTrue(revision.changed_actions)

    def test_10_regional_soil_moisture_is_not_exact_field_moisture(self) -> None:
        _, actions, _ = self.fixture.create_plan()
        moisture = next(action for action in actions if action.action_type == "water_check")
        self.assertIn("not a field sensor", moisture.instructions)

    def test_11_sentinel_constraint_can_block_sourcing_action(self) -> None:
        sentinel = [{"status": "RESTRICTED", "source_record_ids": [self.fixture.source.id], "authority": "TDA"}]
        _, actions, _ = self.fixture.create_plan(context=self.fixture.season_context(sentinel=sentinel))
        self.assertEqual(actions[0].action_type, "inspect_pest")
        self.assertTrue(actions[0].regulatory_conditions)

    def test_12_unresolved_movement_prevents_confident_sourcing(self) -> None:
        sentinel = [{"status": "UNRESOLVED", "source_record_ids": [self.fixture.source.id]}]
        plan, actions, _ = self.fixture.create_plan(context=self.fixture.season_context(sentinel=sentinel))
        self.assertEqual(plan.confidence, "PROVISIONAL")
        self.assertTrue(actions[0].user_confirmation_required)

    def test_13_scholar_evidence_may_inform_planning_basis(self) -> None:
        plan, _, _ = self.fixture.create_plan(context=self.fixture.season_context(scholar=[{"source_record_ids": [self.fixture.source.id]}]))
        self.assertIn(self.fixture.source.id, plan.planning_basis["research_sources"])

    def test_14_scholar_outage_does_not_break_normal_planning(self) -> None:
        plan, actions, _ = self.fixture.create_plan(context=self.fixture.season_context(scholar=[{"status": "PROVIDER_ERROR"}]))
        self.assertTrue(plan.id)
        self.assertTrue(actions)

    def test_15_lunar_context_can_be_displayed(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        self.assertEqual(plan.planning_basis["luna"]["evidence_status"], "Experimental")

    def test_16_lunar_phase_does_not_override_frost_constraints(self) -> None:
        forecast = {"daily_low_c": {"2026-09-29": 4}}
        _, actions, _ = self.fixture.create_plan(context=self.fixture.season_context(forecast=forecast))
        transplant = next(action for action in actions if action.action_type == "transplant")
        self.assertTrue(transplant.environmental_conditions)

    def test_17_preview_creates_zero_external_writes(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        self.assertTrue(preview.event_previews)
        self.assertEqual(self.fixture.calendar_provider.create_calls, 0)

    def test_18_commit_after_approval_creates_fixture_events(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        result = run(self.fixture.calendar.commit_preview(self.fixture.context(), preview_id=preview.id))
        self.assertEqual(result["status"], "COMMITTED")
        self.assertEqual(self.fixture.calendar_provider.create_calls, len(preview.event_previews))

    def test_19_duplicate_commit_is_idempotent(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        run(self.fixture.calendar.commit_preview(self.fixture.context(), preview_id=preview.id))
        calls = self.fixture.calendar_provider.create_calls
        result = run(self.fixture.calendar.commit_preview(self.fixture.context(), preview_id=preview.id))
        self.assertEqual(self.fixture.calendar_provider.create_calls, calls)
        self.assertIn(result["status"], {"ALREADY_COMMITTED", "COMMITTED"})

    def test_20_unauthorized_calendar_create_is_denied(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        result = run(self.fixture.calendar.commit_preview(self.fixture.context(permissions={"tool.read", "calendar.read"}), preview_id=preview.id))
        self.assertIn("permission_denied", result["warnings"])
        self.assertEqual(self.fixture.calendar_provider.create_calls, 0)

    def test_21_calendar_read_does_not_imply_create(self) -> None:
        self.test_20_unauthorized_calendar_create_is_denied()

    def test_22_plan_revision_invalidates_stale_preview(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        self.fixture.connection.execute("UPDATE season_plans SET version = 2 WHERE id = ?", (plan.id,))
        self.fixture.connection.commit()
        result = run(self.fixture.calendar.commit_preview(self.fixture.context(), preview_id=preview.id))
        self.assertEqual(result["status"], "STALE_PREVIEW")
        self.assertEqual(self.fixture.calendar_provider.create_calls, 0)

    def test_23_external_event_id_maps_to_action(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        result = run(self.fixture.calendar.commit_preview(self.fixture.context(), preview_id=preview.id))
        self.assertTrue(result["created"][0]["external_event_id"])
        self.assertTrue(result["created"][0]["action_id"])

    def test_24_calendar_outage_preserves_internal_plan(self) -> None:
        fixture = Phase9Fixture(calendar_unavailable=True)
        try:
            plan, _, _ = fixture.create_plan()
            preview = fixture.calendar.preview_events(fixture.context(), season_plan_id=plan.id, calendar_binding_id=fixture.calendar_binding.id)
            result = run(fixture.calendar.commit_preview(fixture.context(), preview_id=preview.id))
            self.assertEqual(result["status"], "PARTIAL_OR_FAILED")
            self.assertIsNotNone(fixture.repo.get_season_plan(fixture.org.id, plan.id))
        finally:
            fixture.close()

    def test_25_oauth_token_secrets_never_appear_in_logs(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        run(self.fixture.calendar.commit_preview(self.fixture.context(), preview_id=preview.id))
        self.assertNotIn("secret-calendar-token", str(self.fixture.audit.for_request("phase9")))

    def test_26_cross_tenant_calendar_bindings_are_denied(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        with self.assertRaises(PermissionError):
            self.fixture.calendar.preview_events(self.fixture.context(org=self.fixture.other_org, user=self.fixture.other_user, workspace=self.fixture.other_workspace), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)

    def test_27_user_timezone_preserved(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        self.assertEqual(preview.event_previews[0]["start"]["timeZone"], "America/Chicago")

    def test_28_dst_transition_handled_with_local_date(self) -> None:
        request = self.fixture.request(start_date="2026-10-18", end_date="2026-11-15")
        plan, _, _ = self.fixture.create_plan(request=request)
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        self.assertEqual(preview.event_previews[0]["start"]["dateTime"][:10], "2026-10-18")

    def test_29_date_only_window_does_not_shift_due_to_utc(self) -> None:
        plan, actions, _ = self.fixture.create_plan()
        self.assertEqual(plan.start_date, "2026-09-15")
        self.assertEqual(actions[0].preferred_at[:10], "2026-09-15")

    def test_30_recurrence_retains_local_schedule_semantics(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        recurring = [item for item in preview.event_previews if item["recurrence"]]
        self.assertTrue(recurring)
        self.assertEqual(recurring[0]["start"]["timeZone"], "America/Chicago")

    def test_31_fixture_calendar_provider_zero_cost(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        run(self.fixture.calendar.commit_preview(self.fixture.context(), preview_id=preview.id))
        self.assertTrue(all(event["estimated_cost_usd"] == 0.0 for event in self.fixture.ledger.organization_usage(self.fixture.org.id)))

    def test_32_google_calendar_provider_classified_free_oauth_disabled_by_default(self) -> None:
        google = self.fixture.registry.get("google-calendar")
        self.assertEqual(google.billing_class, BillingClass.FREE)
        self.assertEqual(google.authentication_requirement, AuthenticationRequirement.OAUTH)
        self.assertFalse(google.enabled)

    def test_33_no_paid_fallback(self) -> None:
        fixture = Phase9Fixture(calendar_unavailable=True)
        try:
            plan, _, _ = fixture.create_plan()
            preview = fixture.calendar.preview_events(fixture.context(), season_plan_id=plan.id, calendar_binding_id=fixture.calendar_binding.id)
            run(fixture.calendar.commit_preview(fixture.context(), preview_id=preview.id))
            provider_ids = {event["provider_id"] for event in fixture.ledger.organization_usage(fixture.org.id)}
            self.assertNotIn("future-paid-provider", provider_ids)
        finally:
            fixture.close()

    def test_34_season_generation_runs_local_free(self) -> None:
        plan, _, model_run_ids = self.fixture.create_plan()
        self.assertTrue(plan.id)
        self.assertEqual(model_run_ids, [])

    def test_35_calendar_outage_cannot_trigger_paid_service(self) -> None:
        self.test_33_no_paid_fallback()

    def test_36_season_plan_preserves_context_sources(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        self.assertIn(self.fixture.source.id, plan.planning_basis["geo_sources"])

    def test_37_revision_preserves_original_version(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        revision = run(self.fixture.season.revise_plan(self.fixture.context(), plan.id, self.fixture.season_context(forecast={"heavy_rain_dates": ["2026-09-29"]})))
        self.assertEqual(revision.previous_plan_id, plan.id)
        self.assertIsNone(revision.revised_plan_id)

    def test_38_calendar_event_links_back_to_action_and_plan_version(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        result = run(self.fixture.calendar.commit_preview(self.fixture.context(), preview_id=preview.id))
        self.assertEqual(result["created"][0]["plan_version"], plan.version)

    def test_39_completion_outcome_retains_planned_vs_actual_timing(self) -> None:
        plan, actions, _ = self.fixture.create_plan()
        self.fixture.season.complete_action(self.fixture.context(), actions[0].id, "DONE", completed_at="2026-09-16T10:00:00-05:00")
        outcome = self.fixture.repo.create_outcome(Outcome(organization_id=self.fixture.org.id, action_id=actions[0].id, user_plant_id=self.fixture.user_plant.id, planned_at=actions[0].preferred_at, actual_at="2026-09-16T10:00:00-05:00", result="completed"))
        self.assertEqual(outcome.planned_at, actions[0].preferred_at)

    def test_40_model_generated_schedule_reasoning_records_model_run(self) -> None:
        request = self.fixture.request(use_model=True)
        _, _, model_run_ids = self.fixture.create_plan(request=request)
        self.assertEqual(len(model_run_ids), 1)
        self.assertIsNotNone(self.fixture.repo.get_model_run(self.fixture.org.id, model_run_ids[0]))

    def test_41_org_a_cannot_access_org_b_plans(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        self.assertIsNone(self.fixture.repo.get_season_plan(self.fixture.other_org.id, plan.id))

    def test_42_org_a_cannot_access_org_b_calendar_binding(self) -> None:
        self.assertIsNone(self.fixture.repo.get_calendar_binding(self.fixture.other_org.id, self.fixture.calendar_binding.id))

    def test_43_org_a_cannot_commit_org_b_preview(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        preview = self.fixture.calendar.preview_events(self.fixture.context(), season_plan_id=plan.id, calendar_binding_id=self.fixture.calendar_binding.id)
        with self.assertRaises(PermissionError):
            run(self.fixture.calendar.commit_preview(self.fixture.context(org=self.fixture.other_org, user=self.fixture.other_user, workspace=self.fixture.other_workspace), preview_id=preview.id))

    def test_44_shared_public_climate_sources_do_not_leak_private_tenant_data(self) -> None:
        plan, _, _ = self.fixture.create_plan()
        self.assertIn(self.fixture.source.id, plan.planning_basis["climate_sources"])
        self.assertNotIn(str(self.fixture.location.latitude), str(plan.planning_basis))

    def test_gdd_formula_is_deterministic(self) -> None:
        summary = season_gdd_summary(8, 20, "tomato")
        self.assertEqual(summary["base_c"], 10.0)
        self.assertAlmostEqual(summary["gdd_c"], 5.0)

    def test_horizon_boundaries_are_explicit(self) -> None:
        self.assertEqual(horizon_basis(__import__("datetime").date(2026, 11, 20), __import__("datetime").date(2026, 8, 11)), "climate_normals_historical_distribution")


if __name__ == "__main__":
    unittest.main()
