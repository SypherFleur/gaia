# Architecture And Source Reconciliation

Date: 2026-08-14

## Architecture

GAIA now places a LangGraph-compatible GuidancePlan workflow above the existing domain services. The existing custom orchestrator remains in place and owns the established `ChatResult` contract. The graph routes to existing service handlers instead of duplicating specialist business logic.

Active graph nodes:

- `classify_route`
- `geography`
- `environment`
- `economics`
- `season`
- `reasoning`

Guardrails preserved:

- Tool/data calls: Tool Gateway, Cost Firewall, provenance, tenancy, quota/cache, egress policy, audit, and usage ledger.
- Model calls: Model Gateway, local/allowed provider policy, Cost Firewall, audit, usage ledger, structured GuidancePlan validation.
- Calendar writes: preview and explicit commit gate.
- Paid paths: disabled.

## Source Modes

Normal file-backed manual alpha defaults:

- live/free where there is a real adapter: NWS, NASA POWER, GBIF, Europe PMC.
- disabled/unavailable where live support is incomplete or requires credentials: USDA soil, USGS water, Genesys, Kew POWO/WCVP, regulatory decision rules, PlantNet, Google Calendar, USDA NASS/AMS without keys.
- local deterministic where appropriate: GAIA local admin geography.
- fixtures only for in-memory tests or explicit `GAIA_RUNTIME_MODE=demo|fixture|test`.

Kew POWO/WCVP is first-class but documented-only by default pending explicit access review. Its adapter preserves attribution, no-implied-endorsement, terms URL, and source provenance.

## Location Semantics

Locations now carry explicit source metadata:

- `device`: browser geolocation permission supplied coordinates.
- `manual`: user-entered real location.
- `saved`: saved real location.
- `demo_fixture`: explicit test/demo alias.

Normal startup does not activate demo locations. Demo aliases remain selectable for explicit demo use, and responses label them as demo fixtures rather than current device location.

## Operator Commands

- `gaia architecture`
- `gaia sources list`
- `gaia providers list`
- `gaia providers health`

## Cash Status

Automatic paid provider use remains off. Automatic paid model use remains off. Automatic overage remains off. Telemetry remains disabled by default. Current automatic spend target remains `$0.00`; reserve remains `$20.00`.
