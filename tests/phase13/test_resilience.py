from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.request

from packages.providers import HealthStatus, ProviderHealthMonitor
from packages.providers.http_retry import RetryExhausted, request_json


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class CircuitBreakerRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.monitor = ProviderHealthMonitor(failure_threshold=2, cooldown_seconds=60.0, clock=self.clock)

    def test_breaker_opens_after_threshold(self) -> None:
        self.assertEqual(self.monitor.record_failure("nws"), HealthStatus.DEGRADED)
        self.assertEqual(self.monitor.record_failure("nws"), HealthStatus.UNAVAILABLE)
        self.assertEqual(self.monitor.status("nws"), HealthStatus.UNAVAILABLE)

    def test_breaker_half_opens_after_cooldown_so_provider_can_recover(self) -> None:
        self.monitor.record_failure("nws")
        self.monitor.record_failure("nws")
        self.assertEqual(self.monitor.status("nws"), HealthStatus.UNAVAILABLE)

        self.clock.advance(59.0)
        self.assertEqual(self.monitor.status("nws"), HealthStatus.UNAVAILABLE)

        # Past the cooldown one probe is admitted. Without this the gateway
        # denies before it could ever record a success, so the provider would
        # stay dead for the life of the process.
        self.clock.advance(2.0)
        self.assertEqual(self.monitor.status("nws"), HealthStatus.DEGRADED)

    def test_successful_probe_closes_the_circuit(self) -> None:
        self.monitor.record_failure("nws")
        self.monitor.record_failure("nws")
        self.clock.advance(61.0)
        self.monitor.status("nws")

        self.monitor.record_success("nws")

        self.assertEqual(self.monitor.status("nws"), HealthStatus.HEALTHY)
        self.assertEqual(self.monitor.snapshot("nws").consecutive_failures, 0)

    def test_failed_probe_backs_off_further(self) -> None:
        self.monitor.record_failure("nws")
        self.monitor.record_failure("nws")
        self.clock.advance(61.0)
        self.monitor.status("nws")
        self.monitor.record_failure("nws")

        # Second open cycle doubles the cooldown, so a persistently broken
        # provider is probed less often instead of every minute forever.
        self.clock.advance(61.0)
        self.assertEqual(self.monitor.status("nws"), HealthStatus.UNAVAILABLE)
        self.clock.advance(61.0)
        self.assertEqual(self.monitor.status("nws"), HealthStatus.DEGRADED)

    def test_cooldown_is_capped(self) -> None:
        for _ in range(20):
            self.monitor.record_failure("nws")
            self.clock.advance(10_000.0)
            self.monitor.status("nws")

        snapshot = self.monitor.snapshot("nws")
        self.assertIsNotNone(snapshot.status)
        self.assertLessEqual(snapshot.seconds_until_retry or 0.0, 900.0)

    def test_quota_exhausted_is_distinct_from_failure(self) -> None:
        self.monitor.mark_quota_exhausted("nws")
        self.assertEqual(self.monitor.status("nws"), HealthStatus.QUOTA_EXHAUSTED)


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None


class _ScriptedOpener:
    """Opener that replays a scripted sequence of outcomes."""

    def __init__(self, outcomes: list) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def open(self, request, timeout=None):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return _Response(outcome)


class HttpRetryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.slept: list[float] = []

    def _sleep(self, seconds: float) -> None:
        self.slept.append(seconds)

    def test_transient_failure_then_success(self) -> None:
        opener = _ScriptedOpener([urllib.error.URLError("connection reset"), {"ok": True}])

        payload = request_json("https://example.invalid", timeout_seconds=1.0, opener=opener, sleep=self._sleep)

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(opener.calls, 2)
        self.assertEqual(len(self.slept), 1)

    def test_retryable_status_codes_are_retried(self) -> None:
        error = urllib.error.HTTPError("https://example.invalid", 503, "unavailable", {}, None)
        opener = _ScriptedOpener([error, {"ok": True}])

        payload = request_json("https://example.invalid", timeout_seconds=1.0, opener=opener, sleep=self._sleep)

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(opener.calls, 2)

    def test_client_errors_are_not_retried(self) -> None:
        error = urllib.error.HTTPError("https://example.invalid", 404, "not found", {}, None)
        opener = _ScriptedOpener([error, {"ok": True}])

        with self.assertRaises(urllib.error.HTTPError):
            request_json("https://example.invalid", timeout_seconds=1.0, opener=opener, sleep=self._sleep)

        # Retrying a 404 only burns quota; it must fail fast.
        self.assertEqual(opener.calls, 1)
        self.assertEqual(self.slept, [])

    def test_exhaustion_carries_the_underlying_error(self) -> None:
        opener = _ScriptedOpener([urllib.error.URLError("boom")] * 3)

        with self.assertRaises(RetryExhausted) as caught:
            request_json("https://example.invalid", timeout_seconds=1.0, opener=opener, sleep=self._sleep)

        self.assertEqual(caught.exception.attempts, 3)
        self.assertIsInstance(caught.exception.last_error, urllib.error.URLError)
        self.assertEqual(opener.calls, 3)

    def test_backoff_grows_and_is_bounded(self) -> None:
        opener = _ScriptedOpener([urllib.error.URLError("boom")] * 3)

        with self.assertRaises(RetryExhausted):
            request_json(
                "https://example.invalid",
                timeout_seconds=1.0,
                base_delay_seconds=1.0,
                max_delay_seconds=2.0,
                opener=opener,
                sleep=self._sleep,
            )

        self.assertEqual(len(self.slept), 2)
        self.assertTrue(all(0.0 <= delay <= 2.0 for delay in self.slept))


if __name__ == "__main__":
    unittest.main()
