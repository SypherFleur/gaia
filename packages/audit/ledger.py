from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from typing import Any

from packages.domain.models import new_id, now_iso


JsonDict = dict[str, Any]


@dataclass(slots=True)
class UsageEvent:
    organization_id: str
    user_id: str
    provider_id: str
    request_id: str
    status: str
    workspace_id: str | None = None
    tool_id: str | None = None
    model_id: str | None = None
    usage_units: float = 0.0
    estimated_cost_usd: float = 0.0
    actual_cost_usd: float | None = None
    cache_hit: bool = False
    metadata: JsonDict = field(default_factory=dict)
    usage_event_id: str = field(default_factory=new_id)
    started_at: str = field(default_factory=now_iso)
    completed_at: str | None = None


class UsageLedger:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def record(self, event: UsageEvent) -> UsageEvent:
        values = asdict(event)
        values["cache_hit"] = 1 if event.cache_hit else 0
        values["metadata"] = json.dumps(event.metadata, sort_keys=True, separators=(",", ":"))
        columns = list(values)
        self.connection.execute(
            f"INSERT INTO usage_events ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            tuple(values[column] for column in columns),
        )
        self.connection.commit()
        return event

    def organization_usage(self, organization_id: str) -> list[JsonDict]:
        rows = self.connection.execute(
            """
            SELECT * FROM usage_events
            WHERE organization_id = ?
            ORDER BY started_at, usage_event_id
            """,
            (organization_id,),
        ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["cache_hit"] = bool(record["cache_hit"])
            record["metadata"] = json.loads(record["metadata"])
            records.append(record)
        return records

    def estimated_external_spend(self) -> float:
        row = self.connection.execute("SELECT COALESCE(SUM(estimated_cost_usd), 0) AS total FROM usage_events").fetchone()
        return float(row["total"])


@dataclass(slots=True)
class AuditEvent:
    request_id: str
    actor_user_id: str
    organization_id: str
    action: str
    result: str
    workspace_id: str | None = None
    tool_id: str | None = None
    provider_id: str | None = None
    reason: str | None = None
    estimated_cost_usd: float = 0.0
    provenance_record_id: str | None = None
    metadata: JsonDict = field(default_factory=dict)
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_iso)


class AuditLog:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def record(self, event: AuditEvent) -> AuditEvent:
        values = asdict(event)
        values["metadata"] = json.dumps(event.metadata, sort_keys=True, separators=(",", ":"))
        columns = list(values)
        self.connection.execute(
            f"INSERT INTO audit_events ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            tuple(values[column] for column in columns),
        )
        self.connection.commit()
        return event

    def for_request(self, request_id: str) -> list[JsonDict]:
        rows = self.connection.execute(
            "SELECT * FROM audit_events WHERE request_id = ? ORDER BY created_at, id",
            (request_id,),
        ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["metadata"] = json.loads(record["metadata"])
            records.append(record)
        return records

