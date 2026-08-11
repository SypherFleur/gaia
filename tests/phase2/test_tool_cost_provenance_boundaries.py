from __future__ import annotations

import asyncio
import os
import unittest

from packages.audit import AuditLog, UsageLedger
from packages.cache import SQLiteCacheBackend
from packages.cost import CostFirewall, FinancialPolicy, ProviderCostPolicy
from packages.domain import Membership, Organization, User, Workspace
from packages.persistence import GaiaRepository, connect_in_memory, initialize_schema
from packages.policy import DataEgressPolicy
from packages.providers import (
    AuthenticationRequirement,
    BillingClass,
    CachePolicy,
    FreshnessClass,
    HealthStatus,
    LicenseMetadata,
    ProviderHealthMonitor,
    ProviderQuotaPolicy,
    ProviderRecord,
    ProviderRegistry,
    ProviderType,
    QuotaManager,
    default_protocol_two_registry,
)
from packages.provenance import ProvenanceRecord
from packages.status import CostStatusService
from packages.tools import ToolExecutionContext, ToolGateway, ToolRequest, ToolRisk
from packages.tools.mock_tools import MockTool


def run(coro):
    return asyncio.run(coro)


def provider(
    provider_id: str,
    billing_class: BillingClass,
    *,
    enabled: bool = True,
    remote: bool = True,
    daily_requests: int | None = None,
    health_status: HealthStatus = HealthStatus.HEALTHY,
    allow_overage: bool = False,
) -> ProviderRecord:
    return ProviderRecord(
        provider_id=provider_id,
        display_name=provider_id,
        provider_type=ProviderType.MOCK,
        authority="Fixture Authority",
        enabled=enabled,
        billing_class=billing_class,
        cost_policy=ProviderCostPolicy(
            provider_id=provider_id,
            billing_class=billing_class.value,
            hard_monthly_usd=0.0,
            allow_overage=allow_overage,
        ),
        quota_policy=ProviderQuotaPolicy(daily_requests=daily_requests),
        authentication_requirement=AuthenticationRequirement.NONE,
        geographic_scope="fixture",
        cache_policy=CachePolicy(FreshnessClass.SHORT, ttl_seconds=60, stale_if_error_seconds=60),
        license_metadata=LicenseMetadata(),
        attribution="Fixture Authority",
        health_status=health_status,
        remote=remote,
    )


class Phase2Fixture:
    def __init__(self) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.org_a = self.repo.create_organization(Organization(name="Org A", slug="org-a"))
        self.org_b = self.repo.create_organization(Organization(name="Org B", slug="org-b"))
        self.user_a = self.repo.create_user(User(external_auth_id="dev:a", display_name="User A"))
        self.user_b = self.repo.create_user(User(external_auth_id="dev:b", display_name="User B"))
        self.repo.create_membership(
            Membership(
                organization_id=self.org_a.id,
                user_id=self.user_a.id,
                role="owner",
                permissions=["tool.read", "vision.analyze", "regulation.read"],
            )
        )
        self.repo.create_membership(
            Membership(organization_id=self.org_b.id, user_id=self.user_b.id, role="owner", permissions=["tool.read"])
        )
        self.workspace_a = self.repo.create_workspace(
            Workspace(organization_id=self.org_a.id, name="Workspace A", purpose="testing")
        )
        self.workspace_b = self.repo.create_workspace(
            Workspace(organization_id=self.org_b.id, name="Workspace B", purpose="testing")
        )
        self.registry = ProviderRegistry(
            [
                provider("mock-free", BillingClass.FREE, daily_requests=100),
                provider("mock-local", BillingClass.LOCAL, remote=False),
                provider("mock-quota", BillingClass.FREE, daily_requests=0),
                provider("mock-vision-remote", BillingClass.FREE, daily_requests=100),
                provider("mock-regulatory", BillingClass.FREE, daily_requests=100),
                provider("mock-failing", BillingClass.FREE, daily_requests=100),
                provider("mock-paid", BillingClass.MANUAL_PAID, enabled=False),
            ]
        )
        self.ledger = UsageLedger(self.connection)
        self.audit = AuditLog(self.connection)
        self.cache = SQLiteCacheBackend(self.connection)
        self.health = ProviderHealthMonitor(failure_threshold=2)
        self.gateway = ToolGateway(
            connection=self.connection,
            registry=self.registry,
            cost_firewall=CostFirewall(),
            quota_manager=QuotaManager(self.connection),
            cache_backend=self.cache,
            usage_ledger=self.ledger,
            audit_log=self.audit,
            health_monitor=self.health,
        )

    def close(self) -> None:
        self.connection.close()

    def context(
        self,
        *,
        request_id: str = "req-1",
        org_id: str | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        permissions: set[str] | None = None,
        egress_policy: DataEgressPolicy | None = None,
    ) -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id=request_id,
            organization_id=org_id or self.org_a.id,
            user_id=user_id or self.user_a.id,
            workspace_id=workspace_id or self.workspace_a.id,
            permissions=frozenset(permissions or {"tool.read", "vision.analyze", "regulation.read"}),
            data_egress_policy=egress_policy or DataEgressPolicy(),
        )

    def tool(
        self,
        provider_id: str = "mock-free",
        *,
        tool_id: str = "fixture.read",
        permissions: tuple[str, ...] = ("tool.read",),
        risk: ToolRisk = ToolRisk.READ,
        timeout: bool = False,
        include_unknown_fields: bool = False,
    ) -> MockTool:
        return MockTool(
            id=tool_id,
            provider_id=provider_id,
            required_permissions=permissions,
            risk_class=risk,
            timeout=timeout,
            include_unknown_fields=include_unknown_fields,
        )


class CostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase2Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_free_provider_executes(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free"),
                self.fixture.context(request_id="free"),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(
            self.fixture.ledger.organization_usage(self.fixture.org_a.id)[0]["estimated_cost_usd"],
            0.0,
        )

    def test_local_provider_executes(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-local"),
                self.fixture.context(request_id="local"),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "success")

    def test_paid_provider_is_denied_by_default(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-paid"),
                self.fixture.context(request_id="paid-denied"),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "denied")
        self.assertEqual(result.denial_reason, "provider_disabled")

    def test_valid_credentials_do_not_override_denied_paid_policy(self) -> None:
        os.environ["GAIA_TEST_PAID_API_KEY"] = "present-but-not-authority"
        try:
            paid_provider = provider("manual-paid-direct", BillingClass.MANUAL_PAID, enabled=True)
            decision = CostFirewall().check(paid_provider, estimated_cost_usd=0.01)
        finally:
            os.environ.pop("GAIA_TEST_PAID_API_KEY", None)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "manual_paid_provider_denied_by_default")

    def test_estimated_cost_cannot_push_automatic_spend_above_zero(self) -> None:
        free_provider = provider("free-but-costed", BillingClass.FREE, enabled=True)
        decision = CostFirewall(FinancialPolicy(target_development_cash_spend_usd=0.0)).check(
            free_provider,
            estimated_cost_usd=0.01,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "provider_hard_monthly_budget_exceeded")

    def test_no_automatic_overage_path_exists(self) -> None:
        bad_provider = provider("bad-overage", BillingClass.FREE, enabled=True, allow_overage=True)
        decision = CostFirewall().check(bad_provider)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "automatic_overage_paths_are_forbidden")


class QuotaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase2Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_quota_exhaustion_prevents_provider_execution(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-quota"),
                self.fixture.context(request_id="quota-denied"),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "denied")
        self.assertEqual(result.denial_reason, "daily_request_quota_exhausted")

    def test_cache_can_satisfy_after_quota_exhaustion_when_policy_permits(self) -> None:
        provenance = ProvenanceRecord(provider="mock-quota", external_record_id="cached-1")
        run(
            self.fixture.cache.put(
                "weather:austin",
                "mock-quota",
                {"cached": True},
                ttl_seconds=60,
                provenance_reference=provenance.id,
            )
        )

        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-quota"),
                self.fixture.context(request_id="quota-cache"),
                ToolRequest(cache_key="weather:austin"),
            )
        )

        self.assertEqual(result.status, "cache_hit")
        self.assertEqual(result.cache_state.value, "FRESH")
        self.assertEqual(result.provenance[0].id, provenance.id)
        self.assertTrue(self.fixture.ledger.organization_usage(self.fixture.org_a.id)[0]["cache_hit"])

    def test_no_paid_fallback_occurs_after_quota_exhaustion(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-quota"),
                self.fixture.context(request_id="quota-no-paid"),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "denied")
        provider_ids = {event["provider_id"] for event in self.fixture.ledger.organization_usage(self.fixture.org_a.id)}
        self.assertNotIn("mock-paid", provider_ids)


class PermissionAndEgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase2Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_unauthorized_tool_execution_is_denied(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free", permissions=("research.read",)),
                self.fixture.context(request_id="permission-denied", permissions={"tool.read"}),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "denied")
        self.assertEqual(result.denial_reason, "permission_denied")

    def test_cross_tenant_tool_execution_is_denied(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free"),
                self.fixture.context(request_id="cross-tenant", workspace_id=self.fixture.workspace_b.id),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "denied")
        self.assertEqual(result.denial_reason, "workspace_tenant_denied")

    def test_write_permission_is_distinct_from_read_permission(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free", permissions=("calendar.create",), risk=ToolRisk.WRITE),
                self.fixture.context(request_id="write-denied", permissions={"tool.read", "calendar.read"}),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "denied")
        self.assertEqual(result.denial_reason, "permission_denied")

    def test_remote_provider_cannot_receive_private_content_when_egress_forbids_it(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-vision-remote", permissions=("vision.analyze",), tool_id="vision.mock"),
                self.fixture.context(
                    request_id="image-egress-denied",
                    egress_policy=DataEgressPolicy(allow_private_image_egress=False),
                ),
                ToolRequest(contains_private_image=True),
            )
        )

        self.assertEqual(result.status, "denied")
        self.assertEqual(result.denial_reason, "private_image_egress_denied")

    def test_exact_location_cannot_be_sent_remotely_when_disabled(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free"),
                self.fixture.context(
                    request_id="location-egress-denied",
                    egress_policy=DataEgressPolicy(allow_exact_location_egress=False),
                ),
                ToolRequest(contains_exact_location=True),
            )
        )

        self.assertEqual(result.status, "denied")
        self.assertEqual(result.denial_reason, "exact_location_egress_denied")


class ProvenanceFailureAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Phase2Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_successful_tool_execution_creates_provenance(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free"),
                self.fixture.context(request_id="provenance"),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.provenance[0].provider, "mock-free")
        self.assertIsNotNone(result.provenance[0].content_hash)

    def test_missing_source_fields_remain_unknown_or_none(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free", include_unknown_fields=True),
                self.fixture.context(request_id="unknown-fields"),
                ToolRequest(),
            )
        )

        provenance = result.provenance[0]
        self.assertIsNone(provenance.canonical_url)
        self.assertIsNone(provenance.authority)
        self.assertEqual(provenance.license, "unknown")

    def test_cached_results_preserve_provenance_linkage(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free"),
                self.fixture.context(request_id="cache-prime"),
                ToolRequest(cache_key="cache:prime", cache_ttl_seconds=60),
            )
        )
        cached = run(self.fixture.cache.get("cache:prime", "mock-free"))

        self.assertEqual(cached.state.value, "FRESH")
        self.assertEqual(cached.provenance_reference, result.provenance[0].id)

    def test_provider_timeout_produces_controlled_failure(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-failing", timeout=True),
                self.fixture.context(request_id="timeout"),
                ToolRequest(),
            )
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.denial_reason, "provider_timeout")

    def test_repeated_failure_marks_provider_degraded_or_unavailable(self) -> None:
        tool = self.fixture.tool("mock-failing", timeout=True)
        run(self.fixture.gateway.execute(tool, self.fixture.context(request_id="failure-1"), ToolRequest()))
        self.assertEqual(self.fixture.health.status("mock-failing"), HealthStatus.DEGRADED)
        run(self.fixture.gateway.execute(tool, self.fixture.context(request_id="failure-2"), ToolRequest()))
        self.assertEqual(self.fixture.health.status("mock-failing"), HealthStatus.UNAVAILABLE)

    def test_high_risk_regulatory_requests_fail_closed_when_current_verification_unavailable(self) -> None:
        result = run(
            self.fixture.gateway.execute(
                self.fixture.tool(
                    "mock-regulatory",
                    permissions=("regulation.read",),
                    risk=ToolRisk.REGULATED,
                    timeout=True,
                ),
                self.fixture.context(request_id="regulatory-fail-closed"),
                ToolRequest(regulatory_current_required=True),
            )
        )

        self.assertEqual(result.status, "fail_closed")
        self.assertEqual(result.denial_reason, "provider_timeout")

    def test_allowed_request_generates_usage_record(self) -> None:
        run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free"),
                self.fixture.context(request_id="usage"),
                ToolRequest(),
            )
        )

        usage = self.fixture.ledger.organization_usage(self.fixture.org_a.id)
        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]["status"], "success")

    def test_denied_paid_request_generates_audit_record_with_zero_spend(self) -> None:
        run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-paid"),
                self.fixture.context(request_id="audit-paid"),
                ToolRequest(),
            )
        )

        events = self.fixture.audit.for_request("audit-paid")
        self.assertEqual(events[0]["result"], "denied")
        self.assertEqual(events[0]["estimated_cost_usd"], 0.0)

    def test_cache_hit_is_tracked(self) -> None:
        provenance = ProvenanceRecord(provider="mock-quota")
        run(
            self.fixture.cache.put(
                "cache:hit",
                "mock-quota",
                {"ok": "cached"},
                ttl_seconds=60,
                provenance_reference=provenance.id,
            )
        )
        run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-quota"),
                self.fixture.context(request_id="cache-hit-tracked"),
                ToolRequest(cache_key="cache:hit"),
            )
        )

        usage = self.fixture.ledger.organization_usage(self.fixture.org_a.id)
        self.assertTrue(usage[0]["cache_hit"])

    def test_organization_usage_can_be_queried_independently(self) -> None:
        run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free"),
                self.fixture.context(request_id="org-a-usage"),
                ToolRequest(),
            )
        )
        run(
            self.fixture.gateway.execute(
                self.fixture.tool("mock-free"),
                self.fixture.context(
                    request_id="org-b-usage",
                    org_id=self.fixture.org_b.id,
                    user_id=self.fixture.user_b.id,
                    workspace_id=self.fixture.workspace_b.id,
                    permissions={"tool.read"},
                ),
                ToolRequest(),
            )
        )

        self.assertEqual(len(self.fixture.ledger.organization_usage(self.fixture.org_a.id)), 1)
        self.assertEqual(len(self.fixture.ledger.organization_usage(self.fixture.org_b.id)), 1)


class RegistryStatusTests(unittest.TestCase):
    def test_default_registry_contains_protocol_two_providers_without_enabled_manual_paid(self) -> None:
        registry = default_protocol_two_registry()
        provider_ids = {provider.provider_id for provider in registry.all()}

        self.assertIn("nws", provider_ids)
        self.assertIn("nasa-power", provider_ids)
        self.assertIn("usda-nrcs-sda", provider_ids)
        self.assertIn("usgs-water", provider_ids)
        self.assertIn("usda-nass", provider_ids)
        self.assertIn("usda-ams", provider_ids)
        self.assertIn("gbif", provider_ids)
        self.assertIn("genesys-pgr", provider_ids)
        self.assertIn("europe-pmc", provider_ids)
        self.assertIn("plantnet", provider_ids)
        self.assertIn("aphis", provider_ids)
        self.assertIn("google-calendar", provider_ids)
        self.assertIn("ollama-local", provider_ids)
        self.assertIn("llama-cpp-local", provider_ids)
        self.assertIn("nvidia-runtime-future", provider_ids)
        self.assertIn("cloudflare-workers-ai-future", provider_ids)
        self.assertIn("future-paid-provider", provider_ids)
        self.assertFalse(
            any(provider.enabled and provider.billing_class == BillingClass.MANUAL_PAID for provider in registry.all())
        )

    def test_cost_status_reports_paid_providers_disabled(self) -> None:
        fixture = Phase2Fixture()
        try:
            status = CostStatusService(
                registry=fixture.registry,
                usage_ledger=fixture.ledger,
                financial_policy=FinancialPolicy(),
            ).status()
        finally:
            fixture.close()

        self.assertEqual(status["total_development_cash_spent"], 0.0)
        self.assertEqual(status["configured_reserve"], 20.0)
        self.assertFalse(status["paid_providers_enabled"])


if __name__ == "__main__":
    unittest.main()
