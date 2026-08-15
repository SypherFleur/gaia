from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from packages.providers import HealthStatus


# Circuit-breaker cooldown before a failed provider is retried, doubling per
# consecutive open cycle so a persistently broken provider is probed rarely
# while a transient blip recovers within a minute.
DEFAULT_COOLDOWN_SECONDS = 60.0
MAX_COOLDOWN_SECONDS = 900.0


@dataclass(slots=True)
class ProviderHealthState:
    status: HealthStatus = HealthStatus.UNKNOWN
    consecutive_failures: int = 0
    opened_at: float | None = None
    open_cycles: int = 0
    probe_in_flight: bool = False


@dataclass(slots=True)
class ProviderHealthSnapshot:
    provider_id: str
    status: HealthStatus
    consecutive_failures: int
    seconds_until_retry: float | None


class ProviderHealthMonitor:
    """Circuit breaker with a half-open probe.

    A provider that trips the breaker must be able to come back: the gateway
    denies before it would ever record a success, so without a timed probe an
    UNAVAILABLE provider stays dead for the life of the process. After the
    cooldown elapses, exactly one caller is allowed through to test the
    provider; its outcome closes or re-opens the circuit.
    """

    def __init__(
        self,
        failure_threshold: int = 2,
        *,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        max_cooldown_seconds: float = MAX_COOLDOWN_SECONDS,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.max_cooldown_seconds = max_cooldown_seconds
        self._clock = clock or time.monotonic
        self._states: dict[str, ProviderHealthState] = {}

    def status(self, provider_id: str) -> HealthStatus:
        state = self._states.get(provider_id)
        if state is None:
            return HealthStatus.UNKNOWN
        if state.status is HealthStatus.UNAVAILABLE and self._cooldown_elapsed(state):
            # Half-open: let one request through to find out if it recovered.
            state.probe_in_flight = True
            return HealthStatus.DEGRADED
        return state.status

    def record_success(self, provider_id: str) -> None:
        self._states[provider_id] = ProviderHealthState(status=HealthStatus.HEALTHY)

    def record_failure(self, provider_id: str) -> HealthStatus:
        state = self._states.get(provider_id, ProviderHealthState())
        failures = state.consecutive_failures + 1
        if failures >= self.failure_threshold:
            # A failed half-open probe backs the cooldown off further.
            cycles = state.open_cycles + 1 if state.probe_in_flight or state.status is not HealthStatus.UNAVAILABLE else state.open_cycles
            self._states[provider_id] = ProviderHealthState(
                status=HealthStatus.UNAVAILABLE,
                consecutive_failures=failures,
                opened_at=self._clock(),
                open_cycles=cycles,
            )
            return HealthStatus.UNAVAILABLE
        self._states[provider_id] = ProviderHealthState(
            status=HealthStatus.DEGRADED,
            consecutive_failures=failures,
            opened_at=state.opened_at,
            open_cycles=state.open_cycles,
        )
        return HealthStatus.DEGRADED

    def mark_quota_exhausted(self, provider_id: str) -> None:
        self._states[provider_id] = ProviderHealthState(status=HealthStatus.QUOTA_EXHAUSTED)

    def snapshot(self, provider_id: str) -> ProviderHealthSnapshot:
        state = self._states.get(provider_id, ProviderHealthState())
        return ProviderHealthSnapshot(
            provider_id=provider_id,
            status=state.status,
            consecutive_failures=state.consecutive_failures,
            seconds_until_retry=self._seconds_until_retry(state),
        )

    def _cooldown_for(self, state: ProviderHealthState) -> float:
        return min(self.cooldown_seconds * (2 ** max(state.open_cycles - 1, 0)), self.max_cooldown_seconds)

    def _cooldown_elapsed(self, state: ProviderHealthState) -> bool:
        if state.opened_at is None:
            return True
        return (self._clock() - state.opened_at) >= self._cooldown_for(state)

    def _seconds_until_retry(self, state: ProviderHealthState) -> float | None:
        if state.status is not HealthStatus.UNAVAILABLE or state.opened_at is None:
            return None
        remaining = self._cooldown_for(state) - (self._clock() - state.opened_at)
        return max(remaining, 0.0)
