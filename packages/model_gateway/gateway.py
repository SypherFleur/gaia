from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, replace
from typing import Any

from packages.audit import AuditEvent, AuditLog, UsageEvent, UsageLedger
from packages.cost import CostFirewall, FinancialPolicy
from packages.domain import ModelRun
from packages.domain.models import now_iso
from packages.model_gateway.types import ModelProvider, ModelRequest, ModelResponse
from packages.policy import DataEgressPolicy
from packages.providers import BillingClass, ProviderRegistry
from packages.tools import ToolExecutionContext


JsonDict = dict[str, Any]


def _hash_payload(payload: JsonDict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ModelGateway:
    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        registry: ProviderRegistry,
        providers: dict[str, ModelProvider],
        cost_firewall: CostFirewall,
        usage_ledger: UsageLedger,
        audit_log: AuditLog,
    ) -> None:
        self.connection = connection
        self.registry = registry
        self.providers = providers
        self.cost_firewall = cost_firewall
        self.usage_ledger = usage_ledger
        self.audit_log = audit_log

    async def generate(
        self,
        context: ToolExecutionContext,
        provider_id: str,
        request: ModelRequest,
    ) -> ModelResponse:
        request_hash = _hash_payload(asdict(request))
        denial = self._preflight(context, provider_id, request)
        if denial is not None:
            response = ModelResponse(provider_id=provider_id, model="", content="", status="denied", error=denial)
            return self._persist_and_record(context, request, response, request_hash=request_hash)

        provider_record = self.registry.get(provider_id)
        provider = self.providers.get(provider_id)
        if provider is None:
            response = ModelResponse(provider_id=provider_id, model="", content="", status="denied", error="model_provider_not_configured")
            return self._persist_and_record(context, request, response, request_hash=request_hash)

        try:
            response = await provider.generate(request)
        except Exception as exc:
            response = ModelResponse(
                provider_id=provider_id,
                model=getattr(provider, "model", ""),
                content="",
                status="provider_error",
                error=f"provider_failure:{exc.__class__.__name__}",
            )

        if provider_record.billing_class != BillingClass.LOCAL and response.cost_usd > 0:
            response = replace(response, status="denied", error="nonzero_model_cost_denied", content="")

        return self._persist_and_record(context, request, response, request_hash=request_hash)

    def _preflight(self, context: ToolExecutionContext, provider_id: str, request: ModelRequest) -> str | None:
        if not self._membership_exists(context.organization_id, context.user_id):
            return "tenant_membership_denied"
        if not self._workspace_belongs_to_org(context.organization_id, context.workspace_id):
            return "workspace_tenant_denied"
        if "model.chat" not in context.permissions:
            return "model_permission_denied"
        try:
            provider = self.registry.get(provider_id)
        except KeyError:
            return "model_provider_unknown"
        if provider.provider_type.value != "MODEL":
            return "provider_is_not_model"
        if provider.remote:
            policy_denial = self._organization_model_policy_denial(context.organization_id, provider_id, request, provider.remote)
            if policy_denial is not None:
                return policy_denial
            egress_denial = self._egress_denial(context.data_egress_policy, request)
            if egress_denial is not None:
                return egress_denial
        else:
            policy_denial = self._organization_model_policy_denial(context.organization_id, provider_id, request, provider.remote)
            if policy_denial is not None:
                return policy_denial
        decision = self.cost_firewall.check(provider, request.estimated_cost_usd)
        if not decision.allowed:
            return decision.reason
        if provider.billing_class == BillingClass.MANUAL_PAID:
            return "manual_paid_model_denied_by_default"
        if self.cost_firewall.financial_policy.allow_automatic_paid_model_usage:
            return "automatic_paid_model_usage_must_remain_disabled"
        return None

    def _egress_denial(self, policy: DataEgressPolicy, request: ModelRequest) -> str | None:
        if not policy.allow_external_model_egress:
            return "external_model_egress_denied"
        if request.contains_private_text and not policy.allow_private_text_egress:
            return "private_text_egress_denied"
        if request.contains_private_image and not policy.allow_private_image_egress:
            return "private_image_egress_denied"
        if request.contains_private_document and not policy.allow_private_document_egress:
            return "private_document_egress_denied"
        if request.contains_exact_location and not policy.allow_exact_location_egress:
            return "exact_location_egress_denied"
        return None

    def _organization_model_policy_denial(
        self,
        organization_id: str,
        provider_id: str,
        request: ModelRequest,
        provider_is_remote: bool,
    ) -> str | None:
        policy = self._organization_policy(organization_id)
        if policy is None:
            return None
        model_policy = policy.get("model_policy", {})
        egress_policy = policy.get("egress_policy", {})
        allowed_providers = model_policy.get("allowed_model_providers") or model_policy.get("allowed_provider_ids")
        if allowed_providers is not None and provider_id not in allowed_providers:
            return "organization_model_provider_not_allowed"
        allowed_models = model_policy.get("allowed_models")
        requested_model = request.metadata.get("model") if hasattr(request, "metadata") else None
        if allowed_models is not None and requested_model and requested_model not in allowed_models:
            return "organization_model_not_allowed"
        if provider_is_remote and model_policy.get("remote_models_allowed") is False:
            return "organization_remote_models_denied"
        if provider_is_remote and model_policy.get("local_models_required") is True:
            return "organization_local_models_required"
        if provider_is_remote and egress_policy.get("allow_external_model_egress") is False:
            return "organization_external_model_egress_denied"
        if request.contains_private_text and egress_policy.get("allow_private_text_egress") is False:
            return "organization_private_text_egress_denied"
        if request.contains_private_image and egress_policy.get("allow_private_image_egress") is False:
            return "organization_private_image_egress_denied"
        if request.contains_private_document and egress_policy.get("allow_private_document_egress") is False:
            return "organization_private_document_egress_denied"
        return None

    def _organization_policy(self, organization_id: str) -> JsonDict | None:
        try:
            row = self.connection.execute(
                """
                SELECT model_policy, egress_policy
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
            "egress_policy": json.loads(row["egress_policy"]),
        }

    def _persist_and_record(
        self,
        context: ToolExecutionContext,
        request: ModelRequest,
        response: ModelResponse,
        *,
        request_hash: str,
    ) -> ModelResponse:
        response_hash = _hash_payload(
            {
                "provider_id": response.provider_id,
                "model": response.model,
                "content": response.content,
                "status": response.status,
                "error": response.error,
            }
        )
        model_run = ModelRun(
            organization_id=context.organization_id,
            provider=response.provider_id,
            model=response.model,
            model_version=response.model_version,
            local_or_remote="remote" if self._provider_is_remote(response.provider_id) else "local",
            input_modalities=request.input_modalities,
            input_tokens_or_units=response.input_tokens_or_units,
            output_tokens_or_units=response.output_tokens_or_units,
            elapsed_ms=response.elapsed_ms,
            cost_usd=response.cost_usd,
            tool_calls=[],
            prompt_version=request.prompt_version,
            prompt_id=request.prompt_id,
            prompt_hash=request.prompt_hash,
            request_hash=request_hash,
            response_hash=response_hash,
            status=response.status,
            error=response.error,
        )
        self._insert_model_run(model_run)
        self._usage(context, response, request, model_run.id)
        self._audit(context, response, request, model_run.id)
        return replace(response, model_run_id=model_run.id)

    def _insert_model_run(self, model_run: ModelRun) -> None:
        values = asdict(model_run)
        for key in ["input_modalities", "tool_calls", "retention_policy"]:
            values[key] = json.dumps(values[key], sort_keys=True, separators=(",", ":"))
        columns = list(values)
        self.connection.execute(
            f"INSERT INTO model_runs ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            tuple(values[column] for column in columns),
        )
        self.connection.commit()

    def _usage(self, context: ToolExecutionContext, response: ModelResponse, request: ModelRequest, model_run_id: str) -> None:
        self.usage_ledger.record(
            UsageEvent(
                organization_id=context.organization_id,
                user_id=context.user_id,
                workspace_id=context.workspace_id,
                provider_id=response.provider_id,
                model_id=model_run_id,
                request_id=context.request_id,
                usage_units=request.estimated_usage_units,
                estimated_cost_usd=response.cost_usd,
                status=response.status,
                completed_at=now_iso(),
                metadata={"model": response.model, "prompt_id": request.prompt_id},
            )
        )

    def _audit(self, context: ToolExecutionContext, response: ModelResponse, request: ModelRequest, model_run_id: str) -> None:
        self.audit_log.record(
            AuditEvent(
                request_id=context.request_id,
                actor_user_id=context.user_id,
                organization_id=context.organization_id,
                workspace_id=context.workspace_id,
                action="model.generate",
                provider_id=response.provider_id,
                result=response.status,
                reason=response.error or "success",
                estimated_cost_usd=response.cost_usd,
                metadata={
                    "model": response.model,
                    "model_run_id": model_run_id,
                    "prompt_id": request.prompt_id,
                    "prompt_version": request.prompt_version,
                },
            )
        )

    def _provider_is_remote(self, provider_id: str) -> bool:
        try:
            return self.registry.get(provider_id).remote
        except KeyError:
            return True

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
