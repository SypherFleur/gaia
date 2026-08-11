from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from packages.providers.registry import BillingClass, ProviderRecord


class CostDecisionStatus(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True, slots=True)
class FinancialPolicy:
    total_initial_cash_budget_usd: float = 20.0
    target_development_cash_spend_usd: float = 0.0
    target_committed_monthly_infrastructure_usd: float = 0.0
    allow_automatic_paid_model_usage: bool = False
    allow_automatic_paid_api_usage: bool = False
    allow_automatic_overage_billing: bool = False
    current_estimated_external_spend_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class CostDecision:
    status: CostDecisionStatus
    reason: str
    estimated_cost_usd: float = 0.0

    @property
    def allowed(self) -> bool:
        return self.status == CostDecisionStatus.ALLOW


class CostFirewall:
    def __init__(self, financial_policy: FinancialPolicy | None = None) -> None:
        self.financial_policy = financial_policy or FinancialPolicy()

    def check(self, provider: ProviderRecord, estimated_cost_usd: float = 0.0) -> CostDecision:
        if not provider.enabled:
            return CostDecision(CostDecisionStatus.DENY, "provider_disabled", estimated_cost_usd)

        if provider.billing_class == BillingClass.MANUAL_PAID:
            return CostDecision(CostDecisionStatus.DENY, "manual_paid_provider_denied_by_default", estimated_cost_usd)

        if estimated_cost_usd > provider.cost_policy.hard_monthly_usd:
            return CostDecision(CostDecisionStatus.DENY, "provider_hard_monthly_budget_exceeded", estimated_cost_usd)

        if estimated_cost_usd > 0:
            if not self.financial_policy.allow_automatic_paid_api_usage:
                return CostDecision(CostDecisionStatus.DENY, "automatic_paid_api_usage_disabled", estimated_cost_usd)
            if self.financial_policy.current_estimated_external_spend_usd + estimated_cost_usd > self.financial_policy.target_development_cash_spend_usd:
                return CostDecision(CostDecisionStatus.DENY, "development_spend_target_exceeded", estimated_cost_usd)

        if provider.cost_policy.allow_overage or self.financial_policy.allow_automatic_overage_billing:
            return CostDecision(CostDecisionStatus.DENY, "automatic_overage_paths_are_forbidden", estimated_cost_usd)

        return CostDecision(CostDecisionStatus.ALLOW, "zero_spend_policy_allows_request", estimated_cost_usd)

