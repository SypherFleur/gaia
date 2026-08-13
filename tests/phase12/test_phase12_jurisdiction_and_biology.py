from __future__ import annotations

import asyncio
import unittest

from packages.audit import AuditLog, UsageLedger
from packages.botany import BotanistService, FixtureGBIFProvider, FixtureGenesysProvider, GBIFTaxonomyTool, GenesysGermplasmTool
from packages.cache import SQLiteCacheBackend
from packages.context import ContextCompiler
from packages.cost import CostFirewall, ProviderCostPolicy
from packages.domain import Location, Membership, Organization, PlantEntity, User, Workspace
from packages.geospatial import AtlasService
from packages.geospatial.providers import (
    AdminResolution,
    AtlasZone,
    FixtureHardinessProvider,
    FixtureWatershedProvider,
    ProviderStatus,
    RegulatoryZoneResolution,
)
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
from packages.provenance import ProvenanceRecord, content_hash
from packages.sentinel import (
    FixtureAPHISProvider,
    FixtureFloridaFDACSProvider,
    FixtureTexasAgricultureProvider,
    JurisdictionPack,
    JurisdictionPackMetadata,
    JurisdictionPackRegistry,
    RegulationMovementRulesTool,
    USStateJurisdictionPack,
    SentinelService,
    default_authority_registry,
)
from packages.sentinel.geometry import zone_relation
from packages.tools import ToolExecutionContext, ToolGateway


def run(coro):
    return asyncio.run(coro)


def enabled_provider(provider_id: str, provider_type: ProviderType, *, remote: bool = True) -> ProviderRecord:
    billing = BillingClass.LOCAL if not remote else BillingClass.FREE
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


class Phase12GeographyProvider:
    provider_id = "fixture-phase12-geography"

    async def resolve_admin(self, latitude: float, longitude: float, at_time: str | None = None) -> AdminResolution:
        if 33.5 <= latitude <= 35.5 and -119.0 <= longitude <= -117.0:
            return self._admin("United States", "US", "California", "CA", "Los Angeles County", "06037", "America/Los_Angeles")
        if 30.0 <= latitude <= 34.9 and -86.0 <= longitude <= -80.0:
            return self._admin("United States", "US", "Georgia", "GA", "Fulton County", "13121", "America/New_York")
        if 25.7 <= latitude <= 26.4 and -80.6 <= longitude <= -80.0:
            return self._admin("United States", "US", "Florida", "FL", "Broward County", "12011", "America/New_York")
        if 27.0 <= latitude <= 29.5 and -83.0 <= longitude <= -80.0:
            return self._admin("United States", "US", "Florida", "FL", "Orange County", "12095", "America/New_York")
        if 29.0 <= latitude <= 30.2 and -96.0 <= longitude <= -94.0:
            return self._admin("United States", "US", "Texas", "TX", "Harris County", "48201", "America/Chicago")
        if 25.0 <= latitude <= 27.0 and -99.0 <= longitude <= -96.0:
            return self._admin("United States", "US", "Texas", "TX", "Hidalgo County", "48215", "America/Chicago")
        return self._admin("United States", "US", "Texas", "TX", "Travis County", "48453", "America/Chicago")

    def _admin(self, country, country_code, state, state_code, county, fips, timezone) -> AdminResolution:
        return AdminResolution(
            status=ProviderStatus("AVAILABLE"),
            country=country,
            country_code=country_code,
            state_or_region=state,
            state_code=state_code,
            county_or_district=county,
            county_fips=fips,
            timezone=timezone,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=f"{country_code}:{state_code}:{county}",
                    canonical_url="fixture://phase12/geography",
                    authority="Fixture Phase 12 Geography",
                    geographic_scope=f"{country_code}/{state_code}/{county}",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash([country_code, state_code, county]),
                )
            ],
        )


class Phase12RegulatoryGeometryProvider:
    provider_id = "fixture-phase12-regulatory-geometry"

    async def resolve_zones(self, latitude: float, longitude: float, at_time: str | None = None) -> RegulatoryZoneResolution:
        regulatory_zones = [AtlasZone("us-federal", "jurisdiction", "United States federal jurisdiction", "USDA APHIS")]
        quarantine_zones = []
        if 29.0 <= latitude <= 30.2 and -96.0 <= longitude <= -94.0:
            quarantine_zones.append(AtlasZone("tx-hlb-gulf-coast", "quarantine", "Texas Citrus Greening Gulf Coast Quarantined Area", "Texas Department of Agriculture"))
        if 25.0 <= latitude <= 27.0 and -99.0 <= longitude <= -96.0:
            regulatory_zones.append(AtlasZone("tx-citrus-zone", "regulated_zone", "Texas Citrus Zone", "Texas Department of Agriculture"))
        if 27.0 <= latitude <= 29.5 and -83.0 <= longitude <= -80.0:
            quarantine_zones.append(AtlasZone("fl-citrus-statewide", "quarantine", "Florida citrus regulated area", "FDACS"))
        if 25.7 <= latitude <= 26.4 and -80.6 <= longitude <= -80.0:
            quarantine_zones.append(AtlasZone("fl-gals-broward", "quarantine", "Broward County giant African land snail quarantine fixture", "FDACS"))
        return RegulatoryZoneResolution(
            status=ProviderStatus("AVAILABLE"),
            regulatory_zones=regulatory_zones,
            quarantine_zones=quarantine_zones,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-phase12-zones",
                    canonical_url="fixture://phase12/zones",
                    authority="Fixture Phase 12 Regulatory Geometry",
                    geographic_scope="US",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash([latitude, longitude]),
                )
            ],
        )


class Phase12Fixture:
    def __init__(self) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Org", slug="phase12-org"))
        self.user = self.repo.create_user(User(external_auth_id="dev:phase12", display_name="Phase 12 User"))
        self.repo.create_membership(Membership(organization_id=self.org.id, user_id=self.user.id, role="owner", permissions=["tool.read", "regulation.read", "vision.analyze"]))
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Movement", purpose="phase12"))
        self.austin = self.repo.create_location(Location(organization_id=self.org.id, label="Austin", latitude=30.2672, longitude=-97.7431, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.houston = self.repo.create_location(Location(organization_id=self.org.id, label="Houston", latitude=29.7604, longitude=-95.3698, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.hidalgo = self.repo.create_location(Location(organization_id=self.org.id, label="Hidalgo", latitude=26.1, longitude=-98.2, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.orlando = self.repo.create_location(Location(organization_id=self.org.id, label="Orlando", latitude=28.5383, longitude=-81.3792, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.broward = self.repo.create_location(Location(organization_id=self.org.id, label="Broward", latitude=26.1901, longitude=-80.3659, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.georgia = self.repo.create_location(Location(organization_id=self.org.id, label="Georgia", latitude=33.7490, longitude=-84.3880, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.california = self.repo.create_location(Location(organization_id=self.org.id, label="California", latitude=34.0522, longitude=-118.2437, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"))
        self.registry = ProviderRegistry(
            [
                enabled_provider("aphis", ProviderType.REGULATION),
                enabled_provider("texas-agriculture", ProviderType.REGULATION),
                enabled_provider("florida-fdacs", ProviderType.REGULATION),
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
        self.aphis = FixtureAPHISProvider()
        self.texas = FixtureTexasAgricultureProvider()
        self.florida = FixtureFloridaFDACSProvider()
        self.pack_registry = JurisdictionPackRegistry(
            [
                JurisdictionPack(
                    JurisdictionPackMetadata("us_federal", "0.1.0", "U.S. federal", "US", ["usda_aphis"], enabled=True),
                    self.aphis,
                ),
                USStateJurisdictionPack(
                    JurisdictionPackMetadata("us_tx", "0.1.0", "Texas", "US", ["tx_agriculture"], enabled=True),
                    self.texas,
                    state_code="TX",
                ),
                USStateJurisdictionPack(
                    JurisdictionPackMetadata("us_fl", "0.1.0", "Florida", "US", ["fl_fdacs_dpi"], enabled=True),
                    self.florida,
                    state_code="FL",
                ),
            ]
        )
        self.atlas = AtlasService(
            self.repo,
            Phase12GeographyProvider(),
            FixtureWatershedProvider(),
            FixtureHardinessProvider(),
            Phase12RegulatoryGeometryProvider(),
        )
        self.sentinel = SentinelService(
            repository=self.repo,
            tool_gateway=self.gateway,
            context_compiler=ContextCompiler(self.repo, self.atlas, __import__("packages.environment.terra", fromlist=["TerraService"])),
            federal_tool=RegulationMovementRulesTool(self.aphis, "aphis"),
            texas_tool=RegulationMovementRulesTool(self.texas, "texas-agriculture"),
            jurisdiction_registry=self.pack_registry,
        )
        self.sentinel.context_compiler.terra = None

    def context(self) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="phase12",
            organization_id=self.org.id,
            user_id=self.user.id,
            workspace_id=self.workspace.id,
            permissions=frozenset({"tool.read", "regulation.read", "vision.analyze"}),
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

    def close(self) -> None:
        self.connection.close()


class Phase12JurisdictionAndBiologyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase12Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_authority_registry_normalizes_us_authorities(self) -> None:
        registry = default_authority_registry()
        self.assertEqual(registry.get("usda_aphis").authority_level, "federal")
        self.assertEqual(registry.get("fl_fdacs_dpi").jurisdiction, "US/FL")
        self.assertIn("plant", registry.get("tx_agriculture").domain.lower())

    def test_florida_state_pack_loads_without_sentinel_core_edit(self) -> None:
        tools = self.fixture.pack_registry.movement_tools_for(
            {"country_code": "US", "state_code": "TX"},
            {"country_code": "US", "state_code": "FL"},
            {"source_country": None, "destination_country": None},
        )
        self.assertEqual({tool.provider_id for tool in tools}, {"aphis", "texas-agriculture", "florida-fdacs"})

    def test_texas_to_florida_citrus_uses_federal_and_florida_rules(self) -> None:
        decision = self.fixture.check(self.fixture.houston, self.fixture.orlando)
        authorities = {rule["authority"] for rule in decision.applicable_rules}
        self.assertEqual(decision.status, "RESTRICTED")
        self.assertIn("USDA APHIS", authorities)
        self.assertIn("Florida Department of Agriculture and Consumer Services", authorities)
        self.assertTrue(any(rule["rule_id"] == "fdacs-citrus-entry-special-permit" for rule in decision.applicable_rules))

    def test_florida_to_texas_citrus_combines_origin_destination_and_federal_rules(self) -> None:
        decision = self.fixture.check(self.fixture.orlando, self.fixture.hidalgo)
        rule_ids = {rule["rule_id"] for rule in decision.applicable_rules}
        self.assertEqual(decision.status, "CONDITIONAL")
        self.assertIn("aphis-citrus-interstate-certificate", rule_ids)
        self.assertIn("tda-citrus-import-prohibited-without-compliance", rule_ids)
        self.assertIn("fdacs-citrus-exit-certified-nursery", rule_ids)

    def test_florida_to_georgia_fixture_preserves_florida_origin_conditions(self) -> None:
        decision = self.fixture.check(self.fixture.orlando, self.fixture.georgia)
        self.assertEqual(decision.status, "CONDITIONAL")
        self.assertTrue(any(rule["jurisdiction_pack"] == "us_fl" for rule in decision.applicable_rules))
        self.assertFalse(any(rule["jurisdiction_pack"] == "us_tx" for rule in decision.applicable_rules))

    def test_california_fixture_to_texas_uses_destination_state_without_california_pack(self) -> None:
        decision = self.fixture.check(self.fixture.california, self.fixture.hidalgo)
        self.assertEqual(decision.status, "CONDITIONAL")
        self.assertTrue(any(rule["authority"] == "Texas Department of Agriculture" for rule in decision.applicable_rules))
        self.assertFalse(any(rule["jurisdiction_pack"] == "us_ca" for rule in decision.applicable_rules))

    def test_county_boundary_without_applicable_rule_is_not_a_restriction(self) -> None:
        decision = self.fixture.check(self.fixture.austin, self.fixture.georgia, species="Solanum lycopersicum", plant_part="fruit", live_plant=False)
        self.assertEqual(decision.status, "ALLOWED")
        self.assertFalse(decision.applicable_rules)

    def test_soil_attached_broward_quarantine_is_restricted_by_polygon_zone(self) -> None:
        decision = self.fixture.check(self.fixture.broward, self.fixture.orlando, species="Ficus benjamina", plant_part="soil", live_plant=False, soil_attached=True)
        self.assertEqual(decision.status, "RESTRICTED")
        self.assertTrue(any(rule["rule_id"] == "fdacs-gals-broward-regulated-articles" for rule in decision.applicable_rules))

    def test_non_us_to_non_us_jurisdiction_fails_closed(self) -> None:
        decision = self.fixture.check(
            None,
            None,
            source_country="SG",
            destination_country="GH",
            species="Vigna unguiculata",
            plant_part="seed",
            live_plant=False,
        )
        self.assertEqual(decision.status, "UNRESOLVED")
        self.assertIn("non_us_jurisdiction_not_implemented", decision.unresolved_questions)

    def test_regulated_pest_alert_tools_are_invoked_with_reporting_provenance(self) -> None:
        decision = run(
            self.fixture.sentinel.regulated_pest_context(
                self.fixture.context(),
                species="Citrus sinensis",
                location_id=self.fixture.orlando.id,
                visual_hypothesis="possible citrus greening",
            )
        )
        self.assertGreater(self.fixture.florida.alert_calls, 0)
        self.assertTrue(decision.source_record_ids)
        self.assertTrue(any("Preserve photos" in item.get("instruction", "") for item in decision.reporting_requirements))

    def test_geometry_relation_distinguishes_point_and_partial_county(self) -> None:
        zone = {"min_lat": 25.8, "max_lat": 26.3, "min_lon": -80.6, "max_lon": -80.1}
        county = {"min_lat": 25.7, "max_lat": 26.4, "min_lon": -80.7, "max_lon": -80.0}
        self.assertEqual(zone_relation(zone, point=(26.0, -80.2)), "POINT_INSIDE")
        self.assertEqual(zone_relation(zone, point=(27.0, -81.0)), "POINT_OUTSIDE")
        self.assertEqual(zone_relation(zone, county_geometry=county), "COUNTY_PARTIAL")


class Phase12BotanyFixture:
    def __init__(self) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Botany Org", slug="phase12-botany"))
        self.user = self.repo.create_user(User(external_auth_id="dev:phase12-botany", display_name="Phase 12 Botany User"))
        self.repo.create_membership(Membership(organization_id=self.org.id, user_id=self.user.id, role="owner", permissions=["tool.read"]))
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Global Biology", purpose="phase12"))
        self.registry = ProviderRegistry(
            [
                enabled_provider("gbif", ProviderType.TAXONOMY),
                enabled_provider("genesys-pgr", ProviderType.GERMPLASM),
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
        self.botanist = BotanistService(
            self.repo,
            self.gateway,
            GBIFTaxonomyTool(FixtureGBIFProvider()),
            GenesysGermplasmTool(FixtureGenesysProvider()),
        )

    def context(self) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="phase12-botany",
            organization_id=self.org.id,
            user_id=self.user.id,
            workspace_id=self.workspace.id,
            permissions=frozenset({"tool.read"}),
        )

    def model_run_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM model_runs").fetchone()
        return int(row["count"])

    def close(self) -> None:
        self.connection.close()


class Phase12GlobalBiologyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase12BotanyFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_cowpea_profile_contains_source_backed_global_biology(self) -> None:
        lookup = run(self.fixture.botanist.resolve_taxon(self.fixture.context(), "cowpea"))
        germplasm = run(self.fixture.botanist.search_germplasm(self.fixture.context(), "heat tolerant cowpea"))
        profile = self.fixture.botanist.build_plant_profile(
            self.fixture.org.id,
            lookup.plant_entity,
            germplasm_links=germplasm.data["accessions"],
        )

        self.assertEqual(lookup.status, "ACCEPTED")
        self.assertEqual(profile.taxonomy["scientific_name"], "Vigna unguiculata")
        self.assertTrue(profile.native_range)
        self.assertIn("tropical savanna agriculture", profile.biomes)
        self.assertIn("temperature", profile.climate_associations)
        self.assertIn("pulse crop", profile.crop_use["values"])
        self.assertIn("forage", profile.forage_use["values"])
        self.assertTrue(profile.germplasm_links)
        self.assertTrue(profile.occurrence_sources)
        self.assertEqual(profile.field_provenance["native_range"]["provider"], "gbif")
        self.assertEqual(self.fixture.model_run_count(), 0)
        self.assertTrue(all(event["estimated_cost_usd"] == 0.0 for event in self.fixture.ledger.organization_usage(self.fixture.org.id)))

    def test_unknown_plant_profile_does_not_invent_global_fields(self) -> None:
        entity = self.fixture.repo.create_plant_entity(PlantEntity(scientific_name="Mysteria unknownensis", canonical_taxon_id="fixture:unknown"))
        profile = self.fixture.botanist.build_plant_profile(self.fixture.org.id, entity)

        self.assertEqual(profile.native_range, [])
        self.assertEqual(profile.introduced_range, [])
        self.assertEqual(profile.biomes, [])
        self.assertEqual(profile.climate_associations, {})
        self.assertEqual(profile.crop_use, {})
        self.assertEqual(profile.germplasm_links, [])
        self.assertNotIn("native_range", profile.field_provenance)


if __name__ == "__main__":
    unittest.main()
