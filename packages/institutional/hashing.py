from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(value: Any) -> str:
    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def scrub_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        scrubbed = {}
        for key, nested in value.items():
            lower = str(key).lower()
            if any(secret in lower for secret in ["secret", "token", "password", "credential", "api_key"]):
                scrubbed[key] = "[REDACTED]"
            else:
                scrubbed[key] = scrub_secrets(nested)
        return scrubbed
    if isinstance(value, list):
        return [scrub_secrets(item) for item in value]
    return value

