# ADR-008: Calendar Write Permissions

Status: Accepted

## Context

Season may export approved actions to Google Calendar, but calendar writes affect user schedules and require OAuth safety.

## Decision

Calendar integration uses OAuth. Creates and meaningful updates require user confirmation. Deletes require explicit user action. Weather-driven changes create proposed revisions unless a future automation policy explicitly permits automatic rescheduling.

## Consequences

- GAIA must maintain internal `Action.id` to external event mapping.
- Raw OAuth tokens must never be logged.
- Calendar implementation follows core Season functionality.

