from __future__ import annotations

from packages.calendar_gateway.providers import CalendarEventRequest, CalendarEventResult


class FixtureCalendarProvider:
    provider_id = "fixture-calendar"

    def __init__(self, *, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.events: dict[str, dict] = {}
        self.create_calls = 0
        self.deleted: list[str] = []
        self.last_request: CalendarEventRequest | None = None

    async def list_calendars(self, credential_reference: str) -> list[dict]:
        if self.unavailable:
            return []
        return [{"id": "fixture-primary", "summary": "Fixture Calendar", "timeZone": "America/Chicago"}]

    async def create_event(self, credential_reference: str, request: CalendarEventRequest) -> CalendarEventResult:
        self.last_request = request
        if self.unavailable:
            return CalendarEventResult(provider_id=self.provider_id, status="PROVIDER_ERROR", error="calendar_unavailable")
        self.create_calls += 1
        event_id = f"fixture-event-{self.create_calls}"
        event = {
            "id": event_id,
            "summary": request.summary,
            "description": request.description,
            "start": request.start,
            "end": request.end,
            "recurrence": request.recurrence,
            "extendedProperties": request.extended_properties,
        }
        self.events[event_id] = event
        return CalendarEventResult(provider_id=self.provider_id, status="AVAILABLE", external_event_id=event_id, event=event)

    async def update_event(self, credential_reference: str, event_id: str, request: CalendarEventRequest) -> CalendarEventResult:
        if event_id not in self.events:
            return CalendarEventResult(provider_id=self.provider_id, status="NOT_FOUND", error="event_not_found")
        self.events[event_id].update({"summary": request.summary, "description": request.description, "start": request.start, "end": request.end})
        return CalendarEventResult(provider_id=self.provider_id, status="AVAILABLE", external_event_id=event_id, event=self.events[event_id])

    async def delete_event(self, credential_reference: str, calendar_id: str, event_id: str) -> CalendarEventResult:
        self.deleted.append(event_id)
        self.events.pop(event_id, None)
        return CalendarEventResult(provider_id=self.provider_id, status="DELETED", external_event_id=event_id)


class GoogleCalendarProvider:
    provider_id = "google-calendar"

    def __init__(self, *, configured: bool = False) -> None:
        self.configured = configured

    async def list_calendars(self, credential_reference: str) -> list[dict]:
        if not self.configured:
            return []
        raise NotImplementedError("Live Google Calendar OAuth wiring is deferred until credentials are provided.")

    async def create_event(self, credential_reference: str, request: CalendarEventRequest) -> CalendarEventResult:
        if not self.configured:
            return CalendarEventResult(provider_id=self.provider_id, status="UNAVAILABLE", error="google_oauth_not_configured")
        raise NotImplementedError("Live Google Calendar event creation is opt-in future work.")

    async def update_event(self, credential_reference: str, event_id: str, request: CalendarEventRequest) -> CalendarEventResult:
        if not self.configured:
            return CalendarEventResult(provider_id=self.provider_id, status="UNAVAILABLE", error="google_oauth_not_configured")
        raise NotImplementedError("Live Google Calendar event update is opt-in future work.")

    async def delete_event(self, credential_reference: str, calendar_id: str, event_id: str) -> CalendarEventResult:
        if not self.configured:
            return CalendarEventResult(provider_id=self.provider_id, status="UNAVAILABLE", error="google_oauth_not_configured")
        raise NotImplementedError("Live Google Calendar event deletion is opt-in future work.")

