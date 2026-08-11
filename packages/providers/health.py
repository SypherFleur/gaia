from __future__ import annotations

from dataclasses import dataclass

from packages.providers import HealthStatus


@dataclass(slots=True)
class ProviderHealthState:
    status: HealthStatus = HealthStatus.UNKNOWN
    consecutive_failures: int = 0


class ProviderHealthMonitor:
    def __init__(self, failure_threshold: int = 2) -> None:
        self.failure_threshold = failure_threshold
        self._states: dict[str, ProviderHealthState] = {}

    def status(self, provider_id: str) -> HealthStatus:
        return self._states.get(provider_id, ProviderHealthState()).status

    def record_success(self, provider_id: str) -> None:
        self._states[provider_id] = ProviderHealthState(status=HealthStatus.HEALTHY, consecutive_failures=0)

    def record_failure(self, provider_id: str) -> HealthStatus:
        state = self._states.get(provider_id, ProviderHealthState())
        failures = state.consecutive_failures + 1
        status = HealthStatus.UNAVAILABLE if failures >= self.failure_threshold else HealthStatus.DEGRADED
        self._states[provider_id] = ProviderHealthState(status=status, consecutive_failures=failures)
        return status

    def mark_quota_exhausted(self, provider_id: str) -> None:
        self._states[provider_id] = ProviderHealthState(status=HealthStatus.QUOTA_EXHAUSTED, consecutive_failures=0)

