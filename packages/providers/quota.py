from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from packages.providers import ProviderRecord


class QuotaDecisionStatus(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True, slots=True)
class QuotaDecision:
    status: QuotaDecisionStatus
    reason: str
    used_today: int = 0
    remaining_today: int | None = None

    @property
    def allowed(self) -> bool:
        return self.status == QuotaDecisionStatus.ALLOW


class QuotaManager:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def check(self, organization_id: str, provider: ProviderRecord) -> QuotaDecision:
        if provider.quota_policy.daily_requests is None:
            return QuotaDecision(QuotaDecisionStatus.ALLOW, "no_daily_request_quota")

        today_prefix = datetime.now(UTC).date().isoformat()
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS used
            FROM usage_events
            WHERE organization_id = ?
              AND provider_id = ?
              AND started_at LIKE ?
              AND status IN ('allowed', 'success', 'cache_hit')
            """,
            (organization_id, provider.provider_id, f"{today_prefix}%"),
        ).fetchone()
        used = int(row["used"])
        remaining = provider.quota_policy.daily_requests - used
        if remaining <= 0:
            return QuotaDecision(QuotaDecisionStatus.DENY, "daily_request_quota_exhausted", used, 0)
        return QuotaDecision(QuotaDecisionStatus.ALLOW, "daily_request_quota_available", used, remaining)

