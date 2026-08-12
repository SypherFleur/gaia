from __future__ import annotations

from dataclasses import asdict

from packages.calendar_gateway.providers import CalendarEventRequest, CalendarProvider
from packages.provenance import ProvenanceRecord, content_hash
from packages.tools import GaiaTool, ToolExecutionContext, ToolRequest, ToolResult, ToolRisk


class CalendarCreateEventTool(GaiaTool):
    id = "calendar.event.create"
    version = "0.1.0"
    risk_class = ToolRisk.WRITE
    required_permissions = ("calendar.create",)

    def __init__(self, provider: CalendarProvider, provider_id: str) -> None:
        self.provider = provider
        self.provider_id = provider_id

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        payload = request.payload
        event_request = CalendarEventRequest(
            calendar_id=str(payload["calendar_id"]),
            summary=str(payload["summary"]),
            description=str(payload["description"]),
            start=payload["start"],
            end=payload["end"],
            recurrence=payload.get("recurrence", []),
            extended_properties=payload.get("extended_properties", {}),
        )
        result = await self.provider.create_event(str(payload["credential_reference"]), event_request)
        provenance = [
            ProvenanceRecord(
                provider=self.provider_id,
                external_record_id=result.external_event_id,
                authority=self.provider_id,
                license="private user calendar",
                attribution="GAIA user-authorized calendar",
                content_hash=content_hash(asdict(event_request)),
            )
        ] if result.external_event_id else []
        return ToolResult(
            data={"provider_id": result.provider_id, "status": result.status, "external_event_id": result.external_event_id, "event": result.event},
            provenance=provenance,
            status=result.status if result.status != "AVAILABLE" else "success",
            warnings=[result.error] if result.error else [],
        )
