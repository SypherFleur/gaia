from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, replace
from enum import Enum
import json
from typing import Any, Protocol

from packages.audit import AuditEvent, AuditLog, UsageEvent, UsageLedger
from packages.cache import CacheBackend, CacheState
from packages.cost import CostFirewall, FinancialPolicy
from packages.domain.models import now_iso
from packages.permissions import Permission
from packages.policy import DataEgressPolicy
from packages.providers import HealthStatus, ProviderHealthMonitor, ProviderRegistry, QuotaManager
from packages.provenance import ProvenanceRecord


JsonDict = dict[str, Any]


class ToolRisk(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    REGULATED = "REGULATED"
    ACTUATOR = "ACTUATOR"


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    request_id: str
    user_id: str
    organization_id: str
    workspace_id: str
    permissions: frozenset[str]
    deployment_mode: str = "local"
    data_egress_policy: DataEgressPolicy = field(default_factory=DataEgressPolicy)
    cost_policy: FinancialPolicy = field(default_factory=FinancialPolicy)
    timestamp: str = field(default_factory=now_iso)
    conversation_id: str | None = None
    location_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolRequest:
    payload: JsonDict = field(default_factory=dict)
    cache_key: str | None = None
    cache_ttl_seconds: int | None = None
    stale_if_error_seconds: int | None = None
    allow_stale_cache: bool = False
    estimated_usage_units: float = 1.0
    estimated_cost_usd: float = 0.0
    contains_private_text: bool = False
    contains_private_image: bool = False
    contains_private_document: bool = False
    contains_exact_location: bool = False
    regulatory_current_required: bool = False


@dataclass(frozen=True, slots=True)
class ToolResult:
    data: JsonDict
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    freshness: str | None = None
    confidence: float | None = None
    status: str = "success"
    cache_state: CacheState | None = None
    denial_reason: str | None = None

    @classmethod
    def denied(cls, reason: str) -> "ToolResult":
        return cls(data={}, warnings=[reason], status="denied", denial_reason=reason)

    @classmethod
    def failed(cls, reason: str, *, fail_closed: bool = False) -> "ToolResult":
        status = "fail_closed" if fail_closed else "failed"
        return cls(data={}, warnings=[reason], status=status, denial_reason=reason)


class GaiaTool(Protocol):
    id: str
    version: str
    risk_class: ToolRisk
    required_permissions: tuple[str, ...]
    provider_id: str | None

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult: ...


class ToolGateway:
    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        registry: ProviderRegistry,
        cost_firewall: CostFirewall,
        quota_manager: QuotaManager,
        cache_backend: CacheBackend,
        usage_ledger: UsageLedger,
        audit_log: AuditLog,
        health_monitor: ProviderHealthMonitor | None = None,
    ) -> None:
        self.connection = connection
        self.registry = registry
        self.cost_firewall = cost_firewall
        self.quota_manager = quota_manager
        self.cache_backend = cache_backend
        self.usage_ledger = usage_ledger
        self.audit_log = audit_log
        self.health_monitor = health_monitor or ProviderHealthMonitor()

    async def execute(self, tool: GaiaTool, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        denial = self._preflight_without_provider(tool, context)
        if denial is not None:
            self._audit(context, tool, "denied", denial)
            return ToolResult.denied(denial)

        provider = None
        if tool.provider_id is not None:
            try:
                provider = self.registry.get(tool.provider_id)
            except KeyError:
                reason = "provider_unknown"
                self._audit(context, tool, "denied", reason)
                self._usage(context, tool, tool.provider_id, "denied", request)
                return ToolResult.denied(reason)

            if self.health_monitor.status(provider.provider_id) == HealthStatus.UNAVAILABLE:
                reason = "provider_unavailable"
                self._audit(context, tool, "denied", reason, provider.provider_id)
                self._usage(context, tool, provider.provider_id, "denied", request)
                return ToolResult.denied(reason)

            egress_denial = self._egress_denial(provider.remote, context, request)
            if egress_denial is not None:
                self._audit(context, tool, "denied", egress_denial, provider.provider_id)
                self._usage(context, tool, provider.provider_id, "denied", request)
                return ToolResult.denied(egress_denial)

            organization_policy_denial = self._organization_policy_denial(provider.provider_id, context, request, provider.remote)
            if organization_policy_denial is not None:
                self._audit(context, tool, "denied", organization_policy_denial, provider.provider_id)
                self._usage(context, tool, provider.provider_id, "denied", request)
                return ToolResult.denied(organization_policy_denial)

            cost_decision = self.cost_firewall.check(provider, request.estimated_cost_usd)
            if not cost_decision.allowed:
                self._audit(context, tool, "denied", cost_decision.reason, provider.provider_id)
                self._usage(context, tool, provider.provider_id, "denied", request, estimated_cost_usd=0.0)
                return ToolResult.denied(cost_decision.reason)

            quota_decision = self.quota_manager.check(context.organization_id, provider)
            if not quota_decision.allowed:
                self.health_monitor.mark_quota_exhausted(provider.provider_id)
                cached = await self._cache_result_if_allowed(provider.provider_id, request)
                if cached is not None:
                    self._audit(context, tool, "cache_hit", quota_decision.reason, provider.provider_id, cached.provenance[0].id if cached.provenance else None)
                    self._usage(context, tool, provider.provider_id, "cache_hit", request, cache_hit=True)
                    return cached
                self._audit(context, tool, "denied", quota_decision.reason, provider.provider_id)
                self._usage(context, tool, provider.provider_id, "denied", request)
                return ToolResult.denied(quota_decision.reason)

            cached = await self._cache_result_if_allowed(provider.provider_id, request)
            if cached is not None and cached.cache_state == CacheState.FRESH:
                self._audit(context, tool, "cache_hit", "fresh_cache", provider.provider_id, cached.provenance[0].id if cached.provenance else None)
                self._usage(context, tool, provider.provider_id, "cache_hit", request, cache_hit=True)
                return cached

        try:
            result = await tool.execute(context, request)
        except TimeoutError:
            if provider is not None:
                cached = await self._cache_result_if_allowed(provider.provider_id, request)
                if cached is not None:
                    self._audit(context, tool, "cache_hit", "provider_timeout_stale_cache", provider.provider_id, cached.provenance[0].id if cached.provenance else None)
                    self._usage(context, tool, provider.provider_id, "cache_hit", request, cache_hit=True)
                    return cached
            result = self._handle_provider_failure(provider, tool, context, request, "provider_timeout")
            return result
        except Exception as exc:
            if provider is not None:
                cached = await self._cache_result_if_allowed(provider.provider_id, request)
                if cached is not None:
                    self._audit(context, tool, "cache_hit", "provider_failure_stale_cache", provider.provider_id, cached.provenance[0].id if cached.provenance else None)
                    self._usage(context, tool, provider.provider_id, "cache_hit", request, cache_hit=True)
                    return cached
            result = self._handle_provider_failure(provider, tool, context, request, f"provider_failure:{exc.__class__.__name__}")
            return result

        if provider is not None:
            self.health_monitor.record_success(provider.provider_id)
            if request.cache_key is not None and request.cache_ttl_seconds is not None:
                provenance_reference = result.provenance[0].id if result.provenance else None
                await self.cache_backend.put(
                    request.cache_key,
                    provider.provider_id,
                    result.data,
                    request.cache_ttl_seconds,
                    stale_if_error_seconds=request.stale_if_error_seconds,
                    provenance_reference=provenance_reference,
                )
            self._usage(context, tool, provider.provider_id, "success", request, estimated_cost_usd=request.estimated_cost_usd)
            self._audit(context, tool, "allowed", "success", provider.provider_id, result.provenance[0].id if result.provenance else None)
        else:
            self._audit(context, tool, "allowed", "success")
        return result

    def _preflight_without_provider(self, tool: GaiaTool, context: ToolExecutionContext) -> str | None:
        if not self._membership_exists(context.organization_id, context.user_id):
            return "tenant_membership_denied"
        if not self._workspace_belongs_to_org(context.organization_id, context.workspace_id):
            return "workspace_tenant_denied"
        if not set(tool.required_permissions).issubset(context.permissions):
            return "permission_denied"
        if tool.risk_class == ToolRisk.ACTUATOR:
            return "actuator_tools_deferred"
        return None

    def _membership_exists(self, organization_id: str, user_id: str) -> bool:
        row = self.connection.execute(
            """
            SELECT id FROM memberships
            WHERE organization_id = ? AND user_id = ? AND deleted_at IS NULL
            """,
            (organization_id, user_id),
        ).fetchone()
        return row is not None

    def _workspace_belongs_to_org(self, organization_id: str, workspace_id: str) -> bool:
        row = self.connection.execute(
            """
            SELECT id FROM workspaces
            WHERE organization_id = ? AND id = ? AND deleted_at IS NULL
            """,
            (organization_id, workspace_id),
        ).fetchone()
        return row is not None

    def _egress_denial(self, provider_is_remote: bool, context: ToolExecutionContext, request: ToolRequest) -> str | None:
        if not provider_is_remote:
            return None
        policy = context.data_egress_policy
        if request.contains_private_text and not policy.allow_private_text_egress:
            return "private_text_egress_denied"
        if request.contains_private_image and not policy.allow_private_image_egress:
            return "private_image_egress_denied"
        if request.contains_private_document and not policy.allow_private_document_egress:
            return "private_document_egress_denied"
        if request.contains_exact_location and not policy.allow_exact_location_egress:
            return "exact_location_egress_denied"
        return None

    def _organization_policy_denial(
        self,
        provider_id: str,
        context: ToolExecutionContext,
        request: ToolRequest,
        provider_is_remote: bool,
    ) -> str | None:
        policy = self._organization_policy(context.organization_id)
        if policy is None:
            return None
        allowed_providers = policy.get("tool_policy", {}).get("allowed_provider_ids")
        if allowed_providers is not None and provider_id not in allowed_providers:
            return "organization_provider_not_allowed"
        egress = policy.get("egress_policy", {})
        if request.contains_private_text and egress.get("allow_private_text_egress") is False:
            return "organization_private_text_egress_denied"
        if request.contains_private_image and egress.get("allow_private_image_egress") is False:
            return "organization_private_image_egress_denied"
        if request.contains_private_document and egress.get("allow_private_document_egress") is False:
            return "organization_private_document_egress_denied"
        if request.contains_exact_location and egress.get("allow_exact_location_egress") is False:
            return "organization_exact_location_egress_denied"
        if provider_is_remote and egress.get("allow_research_data_egress") is False and request.contains_private_document:
            return "organization_research_data_egress_denied"
        return None

    def _organization_policy(self, organization_id: str) -> JsonDict | None:
        try:
            row = self.connection.execute(
                """
                SELECT model_policy, tool_policy, egress_policy
                FROM organization_policies
                WHERE organization_id = ? AND deleted_at IS NULL
                LIMIT 1
                """,
                (organization_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
        if row is None:
            return None
        return {
            "model_policy": json.loads(row["model_policy"]),
            "tool_policy": json.loads(row["tool_policy"]),
            "egress_policy": json.loads(row["egress_policy"]),
        }

    async def _cache_result_if_allowed(self, provider_id: str, request: ToolRequest) -> ToolResult | None:
        if request.cache_key is None:
            return None
        cache_record = await self.cache_backend.get(
            request.cache_key,
            provider_id,
            allow_stale=request.allow_stale_cache and not request.regulatory_current_required,
        )
        if cache_record.state not in {CacheState.FRESH, CacheState.STALE_ALLOWED}:
            return None
        provenance = []
        if cache_record.provenance_reference is not None:
            provenance.append(
                ProvenanceRecord(
                    id=cache_record.provenance_reference,
                    provider=provider_id,
                    content_hash=cache_record.content_hash,
                    license="unknown",
                )
            )
        return ToolResult(
            data=cache_record.payload or {},
            provenance=provenance,
            warnings=["served_from_cache"],
            status="cache_hit",
            cache_state=cache_record.state,
        )

    def _handle_provider_failure(
        self,
        provider: Any,
        tool: GaiaTool,
        context: ToolExecutionContext,
        request: ToolRequest,
        reason: str,
    ) -> ToolResult:
        provider_id = provider.provider_id if provider is not None else None
        if provider_id is not None:
            self.health_monitor.record_failure(provider_id)
        fail_closed = request.regulatory_current_required
        result = ToolResult.failed(reason, fail_closed=fail_closed)
        self._audit(context, tool, result.status, reason, provider_id)
        self._usage(context, tool, provider_id, result.status, request)
        return result

    def _usage(
        self,
        context: ToolExecutionContext,
        tool: GaiaTool,
        provider_id: str | None,
        status: str,
        request: ToolRequest,
        *,
        cache_hit: bool = False,
        estimated_cost_usd: float | None = None,
    ) -> None:
        if provider_id is None:
            return
        self.usage_ledger.record(
            UsageEvent(
                organization_id=context.organization_id,
                user_id=context.user_id,
                workspace_id=context.workspace_id,
                provider_id=provider_id,
                tool_id=tool.id,
                request_id=context.request_id,
                usage_units=request.estimated_usage_units,
                estimated_cost_usd=estimated_cost_usd if estimated_cost_usd is not None else request.estimated_cost_usd,
                cache_hit=cache_hit,
                status=status,
                completed_at=now_iso(),
            )
        )

    def _audit(
        self,
        context: ToolExecutionContext,
        tool: GaiaTool,
        result: str,
        reason: str,
        provider_id: str | None = None,
        provenance_record_id: str | None = None,
    ) -> None:
        self.audit_log.record(
            AuditEvent(
                request_id=context.request_id,
                actor_user_id=context.user_id,
                organization_id=context.organization_id,
                workspace_id=context.workspace_id
                if self._workspace_belongs_to_org(context.organization_id, context.workspace_id)
                else None,
                action="tool.execute",
                tool_id=tool.id,
                provider_id=provider_id,
                result=result,
                reason=reason,
                estimated_cost_usd=0.0,
                provenance_record_id=provenance_record_id,
                metadata={"risk_class": tool.risk_class.value},
            )
        )


def permission_value(permission: Permission | str) -> str:
    if isinstance(permission, Permission):
        return permission.value
    return permission
