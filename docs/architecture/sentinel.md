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

Phase 8 implemented:

- `us_federal` fixture-backed APHIS boundary.
- `us_tx` fixture-backed Texas Agriculture boundary.
- APHIS/Texas read-only live smoke adapter for safe optional reachability/provenance checks.
- fixture declarations proving `us_fl_fixture` and `sg_fixture` extensibility.

Phase 12 adds:

- a registry-backed jurisdiction pack loader;
- `USStateJurisdictionPack` metadata for future state packs;
- `us_fl` fixture-backed Florida FDACS rules for citrus entry/exit, nursery-stock movement, approved citrus structures, aquatic plant permit context, and Broward giant African land snail regulated articles;
- U.S. federal + origin-state + destination-state aggregation for interstate checks;
- explicit `UNRESOLVED` behavior for non-U.S. to non-U.S. legal movement because international jurisdiction is not implemented in Protocol Two;
- regulated-pest escalation that invokes pest-alert providers and preserves reporting provenance.

International legal packs remain future work. Biological/taxonomic context may be global, but Sentinel jurisdiction remains U.S.-only in Phase 12.

## Source Semantics

Regulatory pages are untrusted content for instructions. Retrieved text cannot change GAIA system policy, Tool Gateway policy, Cost Firewall settings, provider enablement, credentials, privacy rules, or model-routing policy.

Source records preserve provider, authority, source URL, content hash, retrieval timestamp, geographic scope, license/attribution metadata, and effective/verification fields when available.
