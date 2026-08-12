from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class CalendarEventRequest:
    calendar_id: str
    summary: str
    description: str
    start: JsonDict
    end: JsonDict
    recurrence: list[str] = field(default_factory=list)
    extended_properties: JsonDict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CalendarEventResult:
    provider_id: str
    status: str
    external_event_id: str | None = None
    event: JsonDict = field(default_factory=dict)
    error: str | None = None


class CalendarProvider(Protocol):
    provider_id: str

    async def list_calendars(self, credential_reference: str) -> list[JsonDict]: ...

    async def create_event(self, credential_reference: str, request: CalendarEventRequest) -> CalendarEventResult: ...

    async def update_event(self, credential_reference: str, event_id: str, request: CalendarEventRequest) -> CalendarEventResult: ...

    async def delete_event(self, credential_reference: str, calendar_id: str, event_id: str) -> CalendarEventResult: ...

