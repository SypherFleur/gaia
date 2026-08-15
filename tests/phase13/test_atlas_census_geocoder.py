from __future__ import annotations

import asyncio
import unittest

from packages.audit import AuditLog, UsageLedger
from packages.cache import SQLiteCacheBackend
from packages.cost import CostFirewall, ProviderCostPolicy
from packages.domain import Location, Membership, Organization, User, Workspace
from packages.geospatial import AtlasService, CensusGeocoderAdapter, CensusGeographyTool
from packages.geospatial.providers import (
    DisabledHardinessProvider,
    DisabledRegulatoryGeometryProvider,
    DisabledWatershedProvider,
    FixtureGeographyProvider,
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
from packages.tools import ToolExecutionContext, ToolGateway


TRAVIS_PAYLOAD = {
    "result": {
        "geographies": {
            "States": [{"NAME": "Texas", "STUSAB": "TX", "GEOID": "48"}],
            "Counties": [{"NAME": "Travis County", "GEOID": "48453", "BASENAME": "Travis", "STATE": "48", "COUNTY": "453"}],
        }
    }
}


def run(coro):
    return asyncio.run(coro)


class CensusNormalizerTest(unittest.TestCase):
    def test_normalizer_matches_fixture_admin_contract(self) -> None:
        fixture = run(FixtureGeographyProvider().resolve_admin(30.2672, -97.7431))
        live = CensusGeocoderAdapter().normalize_geographies_response(TRAVIS_PAYLOAD, "https://geocoding.geo.census.gov/geocoder/geographies/coordinates")

        self.assertEqual(live.status.status, "AVAILABLE")
        self.assertEqual(live.country_code, fixture.country_code)
        self.assertEqual(live.state_code, "TX")
        self.assertEqual(live.county_or_district, "Travis County")
        self.assertEqual(live.county_fips, "48453")
        self.assertEqual(live.provenance[0].provider, "census-geocoder")
        self.assertIn("Census", live.provenance[0].authority)

    def test_non_us_coordinates_resolve_unresolved_not_fabricated(self) -> None:
        live = CensusGeocoderAdapter().normalize_geographies_response({"result": {"geographies": {}}})

        self.assertEqual(live.status.status, "UNRESOLVED")
        self.assertIsNone(live.county_or_district)
        self.assertIsNone(live.state_code)

    def test_request_url_reduces_coordinate_precision_before_egress(self) -> None:
        adapter = CensusGeocoderAdapter()
        url = adapter.request_url(30.26721899, -97.74312345)

        self.assertIn("y=30.27", url)
        self.assertIn("x=-97.74", url)
        self.assertNotIn("30.26721899", url)
        self.assertNotIn("-97.74312345", url)

    def test_unreachable_endpoint_fails_closed(self) -> None:
        adapter = CensusGeocoderAdapter(base_url="http://127.0.0.1:9", timeout_seconds=0.2)
        result = run(adapter.resolve_admin(30.2672, -97.7431))

        self.assertEqual(result.status.status, "UNAVAILABLE")
        self.assertTrue(str(result.status.reason).startswith("census_"))


class RecordingGeographyProvider:
    provider_id = "census-geocoder"

    def __init__(self) -> None:
        self.calls: list[tuple[float, float]] = []

    async def resolve_admin(self, latitude: float, longitude: float, at_time: str | None = None):
        self.calls.append((latitude, longitude))
        return CensusGeocoderAdapter().normalize_geographies_response(TRAVIS_PAYLOAD)


class AtlasGatewayMediationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org = self.repo.create_organization(Organization(name="Org", slug="census-org"))
        self.user = self.repo.create_user(User(external_auth_id="dev:census", display_name="Census User"))
        self.repo.create_membership(Membership(organization_id=self.org.id, user_id=self.user.id, role="owner", permissions=["tool.read"]))
        self.workspace = self.repo.create_workspace(Workspace(organization_id=self.org.id, name="Garden", purpose="census"))
        billing = BillingClass.FREE
        self.registry = ProviderRegistry(
            [
                ProviderRecord(
                    provider_id="census-geocoder",
                    display_name="U.S. Census Bureau Geocoder",
                    provider_type=ProviderType.GEOGRAPHY,
                    authority="U.S. Census Bureau",
                    enabled=True,
                    billing_class=billing,
                    cost_policy=ProviderCostPolicy(provider_id="census-geocoder", billing_class=billing.value, hard_monthly_usd=0.0, allow_overage=False),
                    quota_policy=ProviderQuotaPolicy(daily_requests=100),
                    authentication_requirement=AuthenticationRequirement.OPTIONAL_API_KEY,
                    geographic_scope="US",
                    cache_policy=CachePolicy(FreshnessClass.LONG, ttl_seconds=86400, stale_if_error_seconds=86400),
                    license_metadata=LicenseMetadata(),
                    attribution="U.S. Census Bureau",
                    remote=True,
                )
            ]
        )
        self.ledger = UsageLedger(self.connection)
        self.gateway = ToolGateway(
            connection=self.connection,
            registry=self.registry,
            cost_firewall=CostFirewall(),
            quota_manager=QuotaManager(self.connection),
            cache_backend=SQLiteCacheBackend(self.connection),
            usage_ledger=self.ledger,
            audit_log=AuditLog(self.connection),
        )
        self.provider = RecordingGeographyProvider()
        self.atlas = AtlasService(
            self.repo,
            FixtureGeographyProvider(),
            DisabledWatershedProvider(),
            DisabledHardinessProvider(),
            DisabledRegulatoryGeometryProvider(),
            tool_gateway=self.gateway,
            geography_tool=CensusGeographyTool(self.provider),
        )
        self.location = self.repo.create_location(
            Location(
                organization_id=self.org.id,
                label="Austin garden",
                latitude=30.26721899,
                longitude=-97.74312345,
                privacy_precision="exact",
                exact_coordinates_authorized=True,
                timezone="America/Chicago",
                country_code="US",
            )
        )

    def tearDown(self) -> None:
        self.connection.close()

    def context(self) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id="census-test",
            organization_id=self.org.id,
            user_id=self.user.id,
            workspace_id=self.workspace.id,
            permissions=frozenset({"tool.read"}),
        )

    def test_live_admin_resolution_routes_through_gateway_with_reduced_coordinates(self) -> None:
        result = run(self.atlas.build_geo_context(self.location, context=self.context()))

        self.assertEqual(result.geo_context.county_or_district, "Travis County")
        self.assertEqual(result.geo_context.county_fips, "48453")
        self.assertEqual(result.provider_statuses["admin"], "AVAILABLE")
        # Even for an exact-precision location, only reduced coordinates
        # reach the remote geography provider.
        self.assertEqual(self.provider.calls, [(30.27, -97.74)])
        usage = self.ledger.organization_usage(self.org.id)
        self.assertTrue(any(event["provider_id"] == "census-geocoder" for event in usage))
        self.assertTrue(all(event["estimated_cost_usd"] == 0.0 for event in usage))

    def test_second_resolution_serves_from_gateway_cache(self) -> None:
        run(self.atlas.build_geo_context(self.location, context=self.context()))
        run(self.atlas.build_geo_context(self.location, context=self.context()))

        self.assertEqual(len(self.provider.calls), 1)
        self.assertEqual(self.ledger.organization_usage(self.org.id)[-1]["status"], "cache_hit")

    def test_without_context_falls_back_to_local_provider_with_no_egress(self) -> None:
        result = run(self.atlas.build_geo_context(self.location))

        self.assertEqual(self.provider.calls, [])
        self.assertEqual(result.geo_context.county_or_district, "Travis County")


if __name__ == "__main__":
    unittest.main()
