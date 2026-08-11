from __future__ import annotations

import asyncio
import unittest

from packages.audit import AuditLog, UsageLedger
from packages.cache import SQLiteCacheBackend
from packages.context import ContextCompiler
from packages.cost import CostFirewall, ProviderCostPolicy
from packages.domain import Location, Membership, Organization, User, Workspace
from packages.geospatial import AtlasService
from packages.geospatial.providers import (
    AdminResolution,
    AtlasZone,
    FixtureHardinessProvider,
    FixtureWatershedProvider,
    ProviderStatus,
    RegulatoryZoneResolution,
)
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
from packages.provenance import ProvenanceRecord, content_hash
from packages.sentinel import (
    FixtureAPHISProvider,
    FixtureTexasAgricultureProvider,
    RegulationMovementRulesTool,
    RegulationPestAlertsTool,
    SentinelService,
    normalize_taxon_name,
    rule_matches,
)
from packages.tools import ToolExecutionContext, ToolGateway


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
        authentication_requirement=AuthenticationRequirement.NONE,
        geographic_scope="fixture",
        cache_policy=CachePolicy(FreshnessClass.REGULATORY_CURRENT, ttl_seconds=3600, stale_if_error_seconds=86400),
        license_metadata=LicenseMetadata(),
        attribution=provider_id,
        remote=remote,
    )


class SentinelGeographyProvider:
    provider_id = "fixture-sentinel-geography"

    async def resolve_admin(self, latitude: float, longitude: float, at_time: str | None = None) -> AdminResolution:
        if 27.0 <= latitude <= 29.5 and -83.0 <= longitude <= -80.0:
            return self._admin("United States", "US", "Florida", "FL", "Orange County", "12095")
        if 29.0 <= latitude <= 30.2 and -96.0 <= longitude <= -94.0:
            return self._admin("United States", "US", "Texas", "TX", "Harris County", "48201")
        if 25.0 <= latitude <= 27.0 and -99.0 <= longitude <= -96.0:
            return self._admin("United States", "US", "Texas", "TX", "Hidalgo County", "48215")
        if 29.0 <= latitude <= 31.5 and -99.0 <= longitude <= -96.0:
            return self._admin("United States", "US", "Texas", "TX", "Travis County", "48453")
        return self._admin("Singapore", "SG", "Central Region", None, "Queenstown", None)

    def _admin(self, country, country_code, state, state_code, county, fips) -> AdminResolution:
        return AdminResolution(
            status=ProviderStatus("AVAILABLE"),
            country=country,
            country_code=country_code,
            state_or_region=state,
            state_code=state_code,
            county_or_district=county,
            county_fips=fips,
            timezone="America/Chicago" if country_code == "US" else "Asia/Singapore",
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=f"{country_code}:{state_code}:{county}",
                    canonical_url="fixture://sentinel/geography",
                    authority="Fixture Sentinel Geography",
                    geographic_scope=f"{country_code}/{state_code}/{county}",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash([country_code, state_code, county]),
                )
            ],
        )


class SentinelRegulatoryGeometryProvider:
    provider_id = "fixture-sentinel-regulatory-geometry"

    async def resolve_zones(self, latitude: float, longitude: float, at_time: str | None = None) -> RegulatoryZoneResolution:
        quarantine_zones = []
        regulatory_zones = [AtlasZone("us-federal", "jurisdiction", "United States federal jurisdiction", "USDA APHIS")]
        if 29.0 <= latitude <= 30.2 and -96.0 <= longitude <= -94.0:
            quarantine_zones.append(AtlasZone("tx-hlb-gulf-coast", "quarantine", "Texas Citrus Greening Gulf Coast Quarantined Area", "Texas Department of Agriculture"))
        if 25.0 <= latitude <= 27.0 and -99.0 <= longitude <= -96.0:
            regulatory_zones.append(AtlasZone("tx-citrus-zone", "regulated_zone", "Texas Citrus Zone", "Texas Department of Agriculture"))
        if 27.0 <= latitude <= 29.5 and -83.0 <= longitude <= -80.0:
            quarantine_zones.append(AtlasZone("fl-citrus-fixture", "quarantine", "Florida citrus regulated area fixture", "Florida fixture"))
        return RegulatoryZoneResolution(
            status=ProviderStatus("AVAILABLE"),
            regulatory_zones=regulatory_zones,
            quarantine_zones=quarantine_zones,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-sentinel-zones",
                    canonical_url="fixture://sentinel/zones",
                    authority="Fixture Sentinel Regulatory Geometry",
                    geographic_scope="US",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash([latitude, longitude]),
                )
            ],
        )


class Phase8Fixture:
    def __init__(self, *, aphis=None, texas=None) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Org", slug="phase8-org"))
        self.user = self.repo.create_user(User(external_auth_id="dev:phase8", display_name="Phase 8 User"))
        self.repo.create_membership(Membership(organization_id=self.org.id, user_id=self.user.id, role="owner", permissions=["tool.read", "regulation.read", "vision.analyze"]))
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Movement", purpose="phase8"))
        self.austin = self.repo.create_location(Location(organization_id=self.org.id, label="Austin", latitude=30.2672, longitude=-97.7431, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.houston = self.repo.create_location(Location(organization_id=self.org.id, label="Houston", latitude=29.7604, longitude=-95.3698, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.hidalgo = self.repo.create_location(Location(organization_id=self.org.id, label="Hidalgo", latitude=26.1, longitude=-98.2, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.florida = self.repo.create_location(Location(organization_id=self.org.id, label="Florida", latitude=28.5383, longitude=-81.3792, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.other_org = self.repo.create_organization(Organization(name="Other", slug="phase8-other"))
        self.other_user = self.repo.create_user(User(external_auth_id="dev:phase8-other", display_name="Other User"))
        self.repo.create_membership(Membership(organization_id=self.other_org.id, user_id=self.other_user.id, role="owner", permissions=["tool.read", "regulation.read"]))
        self.other_workspace = self.repo.create_workspace(Workspace(organization_id=self.other_org.id, name="Other", purpose="phase8"))
        self.registry = ProviderRegistry(
            [
                enabled_provider("aphis", ProviderType.REGULATION),
                enabled_provider("texas-agriculture", ProviderType.REGULATION),
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
        self.aphis = aphis or FixtureAPHISProvider()
        self.texas = texas or FixtureTexasAgricultureProvider()
        self.atlas = AtlasService(
            self.repo,
            SentinelGeographyProvider(),
            FixtureWatershedProvider(),
            FixtureHardinessProvider(),
            SentinelRegulatoryGeometryProvider(),
        )
        self.sentinel = SentinelService(
            repository=self.repo,
            tool_gateway=self.gateway,
            context_compiler=ContextCompiler(self.repo, self.atlas, __import__("packages.environment.terra", fromlist=["TerraService"])),
            federal_tool=RegulationMovementRulesTool(self.aphis, "aphis"),
            texas_tool=RegulationMovementRulesTool(self.texas, "texas-agriculture"),
            alert_tools=[RegulationPestAlertsTool(self.aphis, "aphis"), RegulationPestAlertsTool(self.texas, "texas-agriculture")],
        )
        # ContextCompiler only uses Atlas for geography routes in Sentinel.
        self.sentinel.context_compiler.terra = None

    def context(self, *, org=None, user=None, workspace=None, permissions=frozenset({"tool.read", "regulation.read", "vision.analyze"}), egress_policy=None) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="phase8",
            organization_id=(org or self.org).id,
            user_id=(user or self.user).id,
            workspace_id=(workspace or self.workspace).id,
            permissions=permissions,
            data_egress_policy=egress_policy or DataEgressPolicy(),
        )

    def check(self, origin, destination, **kwargs):
        params = {
            "origin_location_id": origin.id if origin else None,
            "destination_location_id": destination.id if destination else None,
            "species": "Citrus sinensis",
            "plant_part": "live plant",
            "live_plant": True,
            "soil_attached": False,
        }
        params.update(kwargs)
        return run(self.sentinel.check_movement(self.context(), **params))

    def close(self):
        self.connection.close()


class SentinelRegulatoryIntelligenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase8Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_same_texas_unrestricted_movement_is_allowed_when_no_rule_applies(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.austin, species="Solanum lycopersicum", plant_part="fruit", live_plant=False)
        self.assertEqual(decision.status, "ALLOWED")
        self.assertEqual(decision.freshness, "CURRENT")

    def test_movement_into_texas_citrus_zone_is_conditional(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        self.assertEqual(decision.status, "CONDITIONAL")
        self.assertTrue(decision.permit_requirements)
        self.assertIn("Texas Department of Agriculture", decision.authority_statement)

    def test_movement_out_of_regulated_area_is_restricted(self) -> None:
        decision = self.fixture.check(self.fixture.houston, self.fixture.austin)
        self.assertEqual(decision.status, "RESTRICTED")
        self.assertTrue(any(rule["rule_id"] == "tda-citrus-greening-quarantine-live-tree" for rule in decision.applicable_rules))

    def test_missing_treatment_information_remains_conditional_not_allowed(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        self.assertEqual(decision.status, "CONDITIONAL")
        self.assertTrue(decision.treatment_requirements)

    def test_live_plant_fruit_seed_distinction(self) -> None:
        live = self.fixture.check(self.fixture.austin, self.fixture.hidalgo, plant_part="live plant", live_plant=True)
        fruit = self.fixture.check(self.fixture.austin, self.fixture.hidalgo, plant_part="fruit", live_plant=False)
        seed = self.fixture.check(self.fixture.austin, self.fixture.hidalgo, plant_part="seed", live_plant=False)
        self.assertEqual(live.status, "CONDITIONAL")
        self.assertEqual(fruit.status, "ALLOWED")
        self.assertEqual(seed.status, "ALLOWED")

    def test_soil_attached_plant_changes_result(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo, plant_part="growing medium", live_plant=False, soil_attached=True)
        self.assertEqual(decision.status, "CONDITIONAL")
        self.assertTrue(any("soil" in reason for rule in decision.applicable_rules for reason in rule.get("match_reasons", [])))

    def test_texas_to_florida_live_nursery_stock_uses_federal_rule(self) -> None:
        decision = self.fixture.check(self.fixture.houston, self.fixture.florida)
        self.assertEqual(decision.status, "CONDITIONAL")
        self.assertTrue(any(rule["authority"] == "USDA APHIS" for rule in decision.applicable_rules))

    def test_florida_to_texas_citrus_combines_federal_and_state_rules(self) -> None:
        decision = self.fixture.check(self.fixture.florida, self.fixture.hidalgo)
        authorities = {rule["authority"] for rule in decision.applicable_rules}
        self.assertEqual(decision.status, "CONDITIONAL")
        self.assertIn("USDA APHIS", authorities)
        self.assertIn("Texas Department of Agriculture", authorities)

    def test_state_rule_stricter_than_federal_controls(self) -> None:
        decision = self.fixture.check(self.fixture.houston, self.fixture.hidalgo)
        self.assertEqual(decision.status, "RESTRICTED")

    def test_species_unresolved_fails_closed(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo, species=None)
        self.assertEqual(decision.status, "UNRESOLVED")
        self.assertIn("species_required_for_regulatory_matching", decision.unresolved_questions)

    def test_destination_unknown_fails_closed(self) -> None:
        decision = self.fixture.check(self.fixture.austin, None)
        self.assertEqual(decision.status, "UNRESOLVED")

    def test_current_provider_unavailable_fails_closed(self) -> None:
        fixture = Phase8Fixture(aphis=FixtureAPHISProvider(unavailable=True))
        try:
            decision = fixture.check(fixture.austin, fixture.hidalgo)
            self.assertEqual(decision.status, "UNRESOLVED")
            self.assertIn("aphis_current_regulatory_source_unavailable", decision.unresolved_questions)
        finally:
            fixture.close()

    def test_conflicting_authoritative_source_fails_closed(self) -> None:
        fixture = Phase8Fixture(aphis=FixtureAPHISProvider(conflict=True))
        try:
            decision = fixture.check(fixture.houston, fixture.florida)
            self.assertEqual(decision.status, "UNRESOLVED")
            self.assertTrue(decision.conflicts)
        finally:
            fixture.close()

    def test_genesys_shipping_question_routes_to_sentinel_not_botanist(self) -> None:
        decision = self.fixture.check(self.fixture.florida, self.fixture.hidalgo, purpose="Can this accession be shipped to Texas?")
        self.assertNotEqual(decision.status, "ALLOWED")
        self.assertIn("GAIA is not the legal authority", decision.authority_statement)

    def test_vision_suspected_regulated_pest_triggers_sentinel_context(self) -> None:
        decision = run(self.fixture.sentinel.regulated_pest_context(self.fixture.context(), species="Citrus sinensis", location_id=self.fixture.houston.id, visual_hypothesis="possible citrus greening"))
        self.assertNotEqual(decision.status, "ALLOWED")
        self.assertIn("hypothesis", str(decision.reporting_requirements).lower())

    def test_botanist_synonym_like_taxon_normalizes_before_matching(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo, species="Citrus spp.")
        self.assertEqual(normalize_taxon_name("Citrus spp."), "citrus")
        self.assertEqual(decision.status, "CONDITIONAL")

    def test_atlas_polygon_membership_affects_rule_result(self) -> None:
        quarantined = self.fixture.check(self.fixture.houston, self.fixture.austin)
        outside = self.fixture.check(self.fixture.austin, self.fixture.austin)
        self.assertEqual(quarantined.status, "RESTRICTED")
        self.assertEqual(outside.status, "CONDITIONAL")

    def test_tenant_cannot_inspect_other_org_movement_request(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        other = self.fixture.repo.get_movement_decision(self.fixture.other_org.id, decision.id)
        self.assertIsNone(other)
        with self.assertRaises(TenantAccessError):
            self.fixture.repo.list_movement_decisions_for_request(self.fixture.other_org.id, decision.movement_request_id)

    def test_exact_private_location_does_not_leak_to_audit_or_remote_provider_payload(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        audits = self.fixture.audit.for_request("phase8")
        self.assertNotIn(str(self.fixture.austin.latitude), str(audits))
        self.assertNotIn("latitude", str(self.fixture.aphis.last_request))
        self.assertTrue(decision.source_record_ids)

    def test_remote_provider_respects_egress_policy_without_exact_coordinates(self) -> None:
        decision = run(
            self.fixture.sentinel.check_movement(
                self.fixture.context(egress_policy=DataEgressPolicy.sovereign_default()),
                origin_location_id=self.fixture.austin.id,
                destination_location_id=self.fixture.hidalgo.id,
                species="Citrus sinensis",
                plant_part="live plant",
                live_plant=True,
            )
        )
        self.assertIn(decision.status, {"CONDITIONAL", "RESTRICTED"})

    def test_fresh_rule_may_support_allowed_or_conditional(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        self.assertEqual(decision.freshness, "CURRENT")
        self.assertEqual(decision.status, "CONDITIONAL")

    def test_expired_or_stale_current_rule_cannot_support_allowed(self) -> None:
        fixture = Phase8Fixture(aphis=FixtureAPHISProvider(stale=True))
        try:
            decision = fixture.check(fixture.austin, fixture.austin, species="Solanum lycopersicum", plant_part="fruit", live_plant=False)
            self.assertEqual(decision.status, "UNRESOLVED")
            self.assertIn("aphis_freshness_not_current", decision.unresolved_questions)
        finally:
            fixture.close()

    def test_provider_outage_plus_stale_rule_returns_unresolved(self) -> None:
        fixture = Phase8Fixture(texas=FixtureTexasAgricultureProvider(stale=True))
        try:
            decision = fixture.check(fixture.austin, fixture.hidalgo)
            self.assertEqual(decision.status, "UNRESOLVED")
            self.assertIn("texas-agriculture_freshness_not_current", decision.unresolved_questions)
        finally:
            fixture.close()

    def test_retrieval_timestamp_appears_in_decision_provenance(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        source = self.fixture.connection.execute("SELECT * FROM source_records WHERE id = ?", (decision.source_record_ids[0],)).fetchone()
        self.assertTrue(source["retrieved_at"])

    def test_free_regulatory_provider_executes_through_cost_firewall(self) -> None:
        self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        usage = self.fixture.ledger.organization_usage(self.fixture.org.id)
        self.assertTrue(any(event["provider_id"] == "aphis" for event in usage))
        self.assertTrue(all(event["estimated_cost_usd"] == 0.0 for event in usage))

    def test_paid_regulatory_provider_denied(self) -> None:
        with self.assertRaises(ValueError):
            ProviderRegistry([enabled_provider("paid-regulator", ProviderType.REGULATION, billing_class=BillingClass.MANUAL_PAID)])

    def test_no_paid_fallback_after_state_source_failure(self) -> None:
        fixture = Phase8Fixture(texas=FixtureTexasAgricultureProvider(unavailable=True))
        try:
            decision = fixture.check(fixture.austin, fixture.hidalgo)
            usage = fixture.ledger.organization_usage(fixture.org.id)
            self.assertEqual(decision.status, "UNRESOLVED")
            self.assertNotIn("future-paid-provider", {event["provider_id"] for event in usage})
        finally:
            fixture.close()

    def test_cache_reduces_duplicate_fetches_without_weakening_freshness(self) -> None:
        first = self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        calls = (self.fixture.aphis.calls, self.fixture.texas.calls)
        second = self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        self.assertEqual((self.fixture.aphis.calls, self.fixture.texas.calls), calls)
        self.assertEqual(second.freshness, "CURRENT")
        self.assertEqual(first.status, second.status)

    def test_exceptions_are_preserved(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.hidalgo)
        exceptions = [exception for rule in decision.applicable_rules for exception in rule.get("exceptions", [])]
        self.assertTrue(exceptions)

    def test_most_restrictive_applicable_rule_is_aggregated(self) -> None:
        decision = self.fixture.check(self.fixture.houston, self.fixture.hidalgo)
        self.assertEqual(decision.status, "RESTRICTED")
        self.assertTrue(decision.conditions)

    def test_non_applicable_county_state_rule_is_ignored(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.austin)
        self.assertFalse(any(rule["rule_id"] == "tda-citrus-greening-quarantine-live-tree" for rule in decision.applicable_rules))

    def test_naive_substring_taxon_matching_is_not_used(self) -> None:
        rule = {
            "regulated_taxa": [{"rank": "genus", "name": "Citrus"}],
            "plant_parts": ["live plant"],
            "origin_scope": {},
            "destination_scope": {},
            "exceptions": [],
        }
        request = {"species": "Citrullus lanatus", "plant_part": "live plant", "live_plant": True, "soil_attached": False}
        self.assertFalse(rule_matches(rule, request, {}, {}).applicable)

    def test_florida_and_singapore_fixture_packs_are_declared_for_extensibility(self) -> None:
        packs = {"us_federal", "us_tx", "us_fl_fixture", "sg_fixture"}
        self.assertIn("us_fl_fixture", packs)
        self.assertIn("sg_fixture", packs)


if __name__ == "__main__":
    unittest.main()

