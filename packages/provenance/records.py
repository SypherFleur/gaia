from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any

from packages.domain.models import now_iso, new_id


JsonDict = dict[str, Any]


def content_hash(payload: Any) -> str:
    if isinstance(payload, bytes):
        data = payload
    elif isinstance(payload, str):
        data = payload.encode("utf-8")
    else:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    provider: str
    external_record_id: str | None = None
    canonical_url: str | None = None
    authority: str | None = None
    retrieved_at: str = ""
    observed_at: str | None = None
    valid_at: str | None = None
    geographic_scope: str | None = None
    license: str = "unknown"
    attribution: str | None = None
    content_hash: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.retrieved_at:
            object.__setattr__(self, "retrieved_at", now_iso())
        if not self.id:
            object.__setattr__(self, "id", new_id())

    def as_dict(self) -> JsonDict:
        return asdict(self)


class SourceSnapshotStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def put(
        self,
        provider_id: str,
        payload: Any,
        *,
        canonical_url: str | None = None,
        license: str = "unknown",
        attribution: str | None = None,
        tenant_independent: bool = True,
        organization_id: str | None = None,
        metadata: JsonDict | None = None,
    ) -> str:
        snapshot_hash = content_hash(payload)
        self.connection.execute(
            """
            INSERT OR IGNORE INTO source_snapshots (
                content_hash, provider_id, canonical_url, license, attribution, payload,
                created_at, tenant_independent, organization_id, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_hash,
                provider_id,
                canonical_url,
                license,
                attribution,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                now_iso(),
                1 if tenant_independent else 0,
                organization_id,
                json.dumps(metadata or {}, sort_keys=True, separators=(",", ":")),
            ),
        )
        self.connection.commit()
        return snapshot_hash

    def get(self, snapshot_hash: str) -> JsonDict | None:
        row = self.connection.execute(
            "SELECT * FROM source_snapshots WHERE content_hash = ?",
            (snapshot_hash,),
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["payload"] = json.loads(record["payload"])
        record["metadata"] = json.loads(record["metadata"])
        return record

