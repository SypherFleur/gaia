# Calendar Architecture

GAIA Calendar is a provider-neutral execution boundary for approved Season actions.

## Boundary

`CalendarProvider` supports:

```text
list_calendars
create_event
update_event
delete_event
```

GAIA domain objects do not depend on Google response shapes. Phase 9 includes a fixture provider and a Google Calendar adapter boundary. Live Google OAuth/event writes remain opt-in and require credentials supplied later.

## Preview To Commit

Calendar writes require:

```text
SeasonPlan
-> CalendarPreview
-> explicit user approval
-> Calendar commit through Tool Gateway
```

Preview creates no external event. Commit requires a valid preview and matching plan version. Duplicate commits are idempotent through `CalendarEventBinding`.

## Event Content

Events include the action title, instructions, plan name, crop/plant label, and GAIA action ID. Exact private coordinates are not included.

## Timezones

Calendar event previews retain the user's IANA timezone label and date-local agricultural semantics. Date-only planning windows are not converted through UTC in a way that shifts the farm day.

## Failure

If Google or another provider is unavailable, the `SeasonPlan` and internal actions remain valid. The user can retry calendar sync. OAuth expiry should mark the binding expired/disconnected without deleting planned actions.

