from __future__ import annotations

import asyncio
import os
import unittest

from packages.audit import AuditLog, UsageLedger
from packages.cache import SQLiteCacheBackend
from packages.cost import CostFirewall, ProviderCostPolicy
from packages.domain import Membership, Organization, User, Workspace
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
from packages.sentinel import APHIS_CITRUS_URL, ReadOnlyRegulatoryPageAdapter, RegulationRequest, TEXAS_CITRUS_URL
from packages.sentinel import RegulationMovementRulesTool
from packages.tools import ToolExecutionContext, ToolGateway, ToolRequest


def run(coro):
    return asyncio.run(coro)


def enabled_aphis_provider() -> ProviderRecord:
    return ProviderRecord(
        provider_id="aphis",
        display_name="APHIS",
        provider_type=ProviderType.REGULATION,
        authority="USDA APHIS",
        enabled=True,
        billing_class=BillingClass.FREE,
        cost_policy=ProviderCostPolicy(
            provider_id="aphis",
            billing_class=BillingClass.FREE.value,
            hard_monthly_usd=0.0,
            allow_overage=False,
        ),
        quota_policy=ProviderQuotaPolicy(daily_requests=10),
        authentication_requirement=AuthenticationRequirement.NONE,
        geographic_scope="US",
        cache_policy=CachePolicy(FreshnessClass.REGULATORY_CURRENT, ttl_seconds=3600, stale_if_error_seconds=0),
        license_metadata=LicenseMetadata(),
        attribution="USDA APHIS",
        remote=True,
    )


@unittest.skipUnless(os.environ.get("GAIA_RUN_SENTINEL_SMOKE") == "1", "set GAIA_RUN_SENTINEL_SMOKE=1 for live Sentinel smoke")
class SentinelSmokeTest(unittest.TestCase):
    def test_live_official_regulatory_pages_are_reachable_with_provenance(self) -> None:
        provider = ReadOnlyRegulatoryPageAdapter(provider_id="sentinel-smoke", authority="official regulatory source", urls=(APHIS_CITRUS_URL, TEXAS_CITRUS_URL), timeout_seconds=20)
        response = run(provider.movement_rules(RegulationRequest(jurisdiction_pack="smoke")))

        self.assertEqual(response.status, "AVAILABLE")
        self.assertEqual(response.freshness, "CURRENT")
        self.assertEqual(len(response.provenance), 2)

    def test_live_official_regulatory_pages_execute_through_tool_gateway_at_zero_cost(self) -> None:
        connection = connect_in_memory()
        initialize_schema(connection)
        repository = GaiaRepository(connection)
        org = repository.create_organization(Organization(name="Sentinel Smoke", slug="sentinel-smoke"))
        user = repository.create_user(User(external_auth_id="dev:sentinel-smoke", display_name="Sentinel Smoke"))
        repository.create_membership(Membership(organization_id=org.id, user_id=user.id, role="owner", permissions=["tool.read", "regulation.read"]))
        workspace = repository.create_workspace(Workspace(organization_id=org.id, name="Sentinel Smoke", purpose="phase8"))
        ledger = UsageLedger(connection)
        gateway = ToolGateway(
            connection=connection,
            registry=ProviderRegistry([enabled_aphis_provider()]),
            cost_firewall=CostFirewall(),
            quota_manager=QuotaManager(connection),
            cache_backend=SQLiteCacheBackend(connection),
            usage_ledger=ledger,
            audit_log=AuditLog(connection),
        )
        tool = RegulationMovementRulesTool(
            ReadOnlyRegulatoryPageAdapter(provider_id="aphis", authority="official regulatory source", urls=(APHIS_CITRUS_URL, TEXAS_CITRUS_URL), timeout_seconds=20),
            "aphis",
        )
        context = ToolExecutionContext(
            request_id="sentinel-smoke",
            organization_id=org.id,
            user_id=user.id,
            workspace_id=workspace.id,
            permissions=frozenset({"tool.read", "regulation.read"}),
        )

        try:
            result = run(
                gateway.execute(
                    tool,
                    context,
                    ToolRequest(
                        payload={"jurisdiction_pack": "smoke"},
                        cache_key="sentinel-smoke:aphis:official-pages",
                        cache_ttl_seconds=3600,
                        regulatory_current_required=True,
                        estimated_cost_usd=0.0,
                    ),
                )
            )

            self.assertEqual(result.status, "AVAILABLE")
            self.assertEqual(result.data["freshness"], "CURRENT")
            self.assertEqual(len(result.provenance), 2)
            usage = ledger.organization_usage(org.id)
            self.assertEqual(usage[0]["provider_id"], "aphis")
            self.assertEqual(usage[0]["estimated_cost_usd"], 0.0)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
