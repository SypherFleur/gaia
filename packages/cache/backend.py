from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Protocol

from packages.domain.models import now_iso
from packages.provenance import content_hash


JsonDict = dict[str, Any]


class CacheState(str, Enum):
    MISS = "MISS"
    FRESH = "FRESH"
    STALE_ALLOWED = "STALE_ALLOWED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class CacheRecord:
    cache_key: str
    provider_id: str
    state: CacheState
    payload: JsonDict | None = None
    provenance_reference: str | None = None
    content_hash: str | None = None


class CacheBackend(Protocol):
    async def get(self, cache_key: str, provider_id: str, *, allow_stale: bool = False) -> CacheRecord: ...

    async def put(
        self,
        cache_key: str,
        provider_id: str,
        payload: JsonDict,
        ttl_seconds: int,
        *,
        stale_if_error_seconds: int | None = None,
        provenance_reference: str | None = None,
    ) -> CacheRecord: ...

    async def invalidate(self, cache_key: str, provider_id: str) -> None: ...


def _parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


class SQLiteCacheBackend:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    async def get(self, cache_key: str, provider_id: str, *, allow_stale: bool = False) -> CacheRecord:
        row = self.connection.execute(
            """
            SELECT * FROM cache_records
            WHERE cache_key = ? AND provider_id = ?
            """,
            (cache_key, provider_id),
        ).fetchone()
        if row is None:
            return CacheRecord(cache_key, provider_id, CacheState.MISS)

        now = datetime.now(UTC)
        expires_at = _parse_time(row["expires_at"])
        stale_until = _parse_time(row["stale_until"])
        if expires_at is not None and now <= expires_at:
            state = CacheState.FRESH
        elif allow_stale and stale_until is not None and now <= stale_until:
            state = CacheState.STALE_ALLOWED
        else:
            state = CacheState.EXPIRED

        return CacheRecord(
            cache_key=cache_key,
            provider_id=provider_id,
            state=state,
            payload=json.loads(row["payload"]),
            provenance_reference=row["provenance_reference"],
            content_hash=row["content_hash"],
        )

    async def put(
        self,
        cache_key: str,
        provider_id: str,
        payload: JsonDict,
        ttl_seconds: int,
        *,
        stale_if_error_seconds: int | None = None,
        provenance_reference: str | None = None,
    ) -> CacheRecord:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl_seconds)
        stale_until = None
        if stale_if_error_seconds is not None:
            stale_until = expires_at + timedelta(seconds=stale_if_error_seconds)
        payload_hash = content_hash(payload)
        self.connection.execute(
            """
            INSERT INTO cache_records (
                cache_key, provider_id, created_at, expires_at, stale_until,
                content_hash, provenance_reference, payload, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}')
            ON CONFLICT(cache_key, provider_id) DO UPDATE SET
                created_at = excluded.created_at,
                expires_at = excluded.expires_at,
                stale_until = excluded.stale_until,
                content_hash = excluded.content_hash,
                provenance_reference = excluded.provenance_reference,
                payload = excluded.payload
            """,
            (
                cache_key,
                provider_id,
                now_iso(),
                expires_at.isoformat(),
                stale_until.isoformat() if stale_until else None,
                payload_hash,
                provenance_reference,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
            ),
        )
        self.connection.commit()
        return CacheRecord(cache_key, provider_id, CacheState.FRESH, payload, provenance_reference, payload_hash)

    async def invalidate(self, cache_key: str, provider_id: str) -> None:
        self.connection.execute(
            "DELETE FROM cache_records WHERE cache_key = ? AND provider_id = ?",
            (cache_key, provider_id),
        )
        self.connection.commit()

