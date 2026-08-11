from __future__ import annotations

from dataclasses import dataclass

from packages.audit import UsageLedger
from packages.cost import FinancialPolicy
from packages.providers import ProviderRegistry


@dataclass(slots=True)
class CostStatusService:
    registry: ProviderRegistry
    usage_ledger: UsageLedger
    financial_policy: FinancialPolicy

    def status(self) -> dict:
        providers = self.registry.all()
        return {
            "total_development_cash_spent": 0.0,
            "configured_reserve": self.financial_policy.total_initial_cash_budget_usd,
            "current_estimated_external_spend": self.usage_ledger.estimated_external_spend(),
            "providers_enabled": [provider.provider_id for provider in providers if provider.enabled],
            "providers_disabled": [provider.provider_id for provider in providers if not provider.enabled],
            "free_quotas": {
                provider.provider_id: {
                    "daily_requests": provider.quota_policy.daily_requests,
                    "remaining": None,
                }
                for provider in providers
                if provider.quota_policy.daily_requests is not None
            },
            "paid_providers_enabled": any(
                provider.enabled and provider.billing_class.value == "MANUAL_PAID"
                for provider in providers
            ),
        }

