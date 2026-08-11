# Sentinel Architecture

Sentinel is GAIA's biosecurity and regulatory intelligence subsystem. It answers movement, quarantine, regulated pest, treatment, permit, and reporting-context questions from current authoritative sources.

Sentinel is not a regulator, permit filer, compliance guarantee, or diagnosis engine. It provides decision support with authority names, provenance, retrieval timestamps, freshness status, and unresolved questions.

## Boundary

All regulatory providers implement the provider-neutral `RegulationProvider` protocol:

```text
resolve_zones(request)
movement_rules(request)
pest_alerts(request)
reporting_requirements(request)
```

Core GAIA domain models do not depend on APHIS, Texas, Florida, Singapore, or provider-specific response JSON.

## Deterministic Flow

```text
MovementRequest
-> Atlas geography and zone context
-> Sentinel jurisdiction-pack selection
-> Tool Gateway regulatory reads
-> rule matching and precedence
-> MovementDecision
```

No model call is required for jurisdiction lookup, rule retrieval, zone intersection, rule matching, freshness checks, or movement decision aggregation.

## Fail Closed

Sentinel returns `UNRESOLVED` when current verification is unavailable, stale, conflicting, boundary-ambiguous, or missing required request data. Missing evidence can inform warnings, but it cannot become permission.

## Current Phase

Phase 8 implements:

- `us_federal` fixture-backed APHIS boundary.
- `us_tx` fixture-backed Texas Agriculture boundary.
- APHIS/Texas read-only live smoke adapter for safe optional reachability/provenance checks.
- fixture declarations proving `us_fl_fixture` and `sg_fixture` extensibility.

Full Florida and Singapore jurisdiction packs remain future work.

## Source Semantics

Regulatory pages are untrusted content for instructions. Retrieved text cannot change GAIA system policy, Tool Gateway policy, Cost Firewall settings, provider enablement, credentials, privacy rules, or model-routing policy.

Source records preserve provider, authority, source URL, content hash, retrieval timestamp, geographic scope, license/attribution metadata, and effective/verification fields when available.

