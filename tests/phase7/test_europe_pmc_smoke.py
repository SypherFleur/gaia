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
from packages.research import EuropePMCAdapter, EuropePMCFetchTool, EuropePMCSearchTool, ScholarService
from packages.tools import ToolExecutionContext, ToolGateway


def run(coro):
    return asyncio.run(coro)


def europe_pmc_provider() -> ProviderRecord:
    return ProviderRecord(
        provider_id="europe-pmc",
        display_name="Europe PMC",
        provider_type=ProviderType.RESEARCH,
        authority="Europe PMC",
        enabled=True,
        billing_class=BillingClass.FREE,
        cost_policy=ProviderCostPolicy(provider_id="europe-pmc", billing_class="FREE", hard_monthly_usd=0.0, allow_overage=False),
        quota_policy=ProviderQuotaPolicy(daily_requests=20),
        authentication_requirement=AuthenticationRequirement.NONE,
        geographic_scope="global",
        cache_policy=CachePolicy(FreshnessClass.MEDIUM, ttl_seconds=86400, stale_if_error_seconds=86400),
        license_metadata=LicenseMetadata(),
        attribution="Europe PMC",
        remote=True,
    )


@unittest.skipUnless(os.environ.get("GAIA_RUN_RESEARCH_SMOKE") == "1", "set GAIA_RUN_RESEARCH_SMOKE=1 for live Europe PMC smoke")
class EuropePMCSmokeTest(unittest.TestCase):
    def test_live_europe_pmc_search_through_gateway_zero_cost(self) -> None:
        connection = connect_in_memory()
        initialize_schema(connection)
        try:
            repo = GaiaRepository(connection)
            org = repo.create_organization(Organization(name="Smoke Org", slug="phase7-smoke"))
            user = repo.create_user(User(external_auth_id="dev:phase7-smoke", display_name="Smoke User"))
            repo.create_membership(Membership(organization_id=org.id, user_id=user.id, role="owner", permissions=["research.read"]))
            workspace = repo.create_workspace(Workspace(organization_id=org.id, name="Smoke", purpose="phase7"))
            ledger = UsageLedger(connection)
            gateway = ToolGateway(
                connection=connection,
                registry=ProviderRegistry([europe_pmc_provider()]),
                cost_firewall=CostFirewall(),
                quota_manager=QuotaManager(connection),
                cache_backend=SQLiteCacheBackend(connection),
                usage_ledger=ledger,
                audit_log=AuditLog(connection),
            )
            provider = EuropePMCAdapter(timeout_seconds=20)
            scholar = ScholarService(
                repository=repo,
                tool_gateway=gateway,
                search_tool=EuropePMCSearchTool(provider),
                fetch_tool=EuropePMCFetchTool(provider),
            )
            context = ToolExecutionContext(request_id="phase7-smoke", organization_id=org.id, user_id=user.id, workspace_id=workspace.id, permissions=frozenset({"research.read"}))
            result = run(scholar.search(context, "tomato blossom end rot calcium", limit=2))

            self.assertTrue(result.works)
            self.assertTrue(result.source_record_ids)
            self.assertEqual(ledger.estimated_external_spend(), 0.0)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()

