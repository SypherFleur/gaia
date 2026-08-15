from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from typing import Any, Callable


# Transient upstream states worth a second attempt. 4xx other than 429 are the
# caller's fault and are never retried — retrying them just wastes quota.
RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})

DEFAULT_ATTEMPTS = 3
DEFAULT_BASE_DELAY_SECONDS = 0.5
DEFAULT_MAX_DELAY_SECONDS = 8.0


class RetryExhausted(Exception):
    """Raised when every attempt failed; carries the final underlying error."""

    def __init__(self, attempts: int, last_error: Exception) -> None:
        super().__init__(f"request failed after {attempts} attempts: {last_error.__class__.__name__}")
        self.attempts = attempts
        self.last_error = last_error


def request_json(
    request: urllib.request.Request | str,
    *,
    timeout_seconds: float,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
    max_delay_seconds: float = DEFAULT_MAX_DELAY_SECONDS,
    opener: Any | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict:
    """Fetch and decode JSON, retrying only genuinely transient failures.

    Retries connection errors, timeouts, and retryable HTTP status codes with
    exponential backoff plus jitter. A non-retryable HTTPError (404, 400, 401)
    is raised immediately so callers can map it to a precise provider status
    instead of waiting out pointless retries.
    """
    pause = sleep or time.sleep
    open_url = opener.open if opener is not None else urllib.request.urlopen
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            with open_url(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS_CODES:
                raise
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_error = exc

        if attempt < attempts:
            pause(_backoff_delay(attempt, base_delay_seconds, max_delay_seconds))

    raise RetryExhausted(attempts, last_error or RuntimeError("unknown request failure"))


def _backoff_delay(attempt: int, base_delay_seconds: float, max_delay_seconds: float) -> float:
    # Full jitter: spreads retries so a recovering upstream is not hit by every
    # caller simultaneously.
    ceiling = min(base_delay_seconds * (2 ** (attempt - 1)), max_delay_seconds)
    return random.uniform(0.0, ceiling)
