from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ProviderCostPolicy:
    provider_id: str
    billing_class: Literal["FREE", "LOCAL", "MANUAL_PAID"]
    hard_monthly_usd: float = 0.0
    allow_overage: bool = False
    hard_daily_requests: int | None = None
    hard_daily_compute_units: int | None = None
    quota_reset: str | None = None


def zero_spend_policy(provider_id: str, billing_class: Literal["FREE", "LOCAL"] = "LOCAL") -> ProviderCostPolicy:
    return ProviderCostPolicy(
        provider_id=provider_id,
        billing_class=billing_class,
        hard_monthly_usd=0.0,
        allow_overage=False,
    )
