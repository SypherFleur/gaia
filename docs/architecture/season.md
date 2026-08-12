# Season Architecture

Season converts GAIA context into structured, revisable agricultural plans. It combines Botanist, Terra, Atlas, Sentinel, optional Scholar evidence, user constraints, plant history, climate timing, and forecast context into `SeasonPlan` and `Action` records.

Season owns planning semantics. Google Calendar is only an execution surface for approved actions.

## Planning Context

`SeasonContext` contains workspace, location, `GeoContext`, `EnvironmentalSnapshot`, climate context, weather forecast context, crop entities, user plants, plant profiles, observations, Sentinel constraints, optional Scholar evidence, user objectives, resource constraints, date range, timezone, and experimental Luna context.

Season can run without Google Calendar connected.

## Horizons

Season distinguishes timing bases:

- `90+ days`: climate normals and historical distributions.
- `30-90 days`: climatological or seasonal context.
- `7-14 days`: forecast begins influencing timing.
- `0-7 days`: forecast materially affects execution.
- same day: current conditions and local observations.

Long-range plans must not pretend to know future weather. Actions record their timing basis.

## Actions

Season actions support action type, crop/plant linkage, earliest/preferred/latest windows, duration, recurrence, dependencies, weather sensitivity, environmental conditions, regulatory conditions, confirmation requirements, calendar mapping, and completion status.

Recurring watering is intentionally modeled as moisture checks unless evidence supports fixed irrigation.

## Revisions

Plan revisions never overwrite historical plans silently. `SeasonPlanRevision` records previous plan, changed actions, unchanged actions, reason, context change, and generation timestamp. Calendar changes still require user approval.

## Luna

Luna remains experimental. It can be displayed as context, but its influence on Phase 9 plans is `None` and it cannot override frost, heat, crop biology, Sentinel, or weather constraints.

