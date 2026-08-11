from __future__ import annotations

from dataclasses import dataclass

from packages.provenance import ProvenanceRecord, content_hash
from packages.tools import ToolExecutionContext, ToolRequest, ToolResult, ToolRisk


@dataclass(slots=True)
class MockTool:
    id: str
    provider_id: str
    required_permissions: tuple[str, ...] = ("tool.read",)
    risk_class: ToolRisk = ToolRisk.READ
    version: str = "1.0.0"
    response_data: dict | None = None
    include_unknown_fields: bool = False
    timeout: bool = False

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        if self.timeout:
            raise TimeoutError("mock timeout")
        data = self.response_data or {"ok": True, "request_id": context.request_id}
        provenance = ProvenanceRecord(
            provider=self.provider_id,
            external_record_id=None if self.include_unknown_fields else "fixture-1",
            canonical_url=None if self.include_unknown_fields else "https://example.invalid/source",
            authority=None if self.include_unknown_fields else "Fixture Authority",
            geographic_scope=None if self.include_unknown_fields else "fixture",
            license="unknown",
            attribution=None if self.include_unknown_fields else "Fixture Authority",
            content_hash=content_hash(data),
        )
        return ToolResult(data=data, provenance=[provenance], freshness="fixture", confidence=1.0)

