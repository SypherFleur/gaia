# GAIA

GAIA is a multimodal agricultural intelligence and guidance system for Cillian Industries.

The governing specification is `GAIA_MASTER_BUILD_PLAN.md`. The primary product object is `GuidancePlan`, not a chat transcript.

## Protocol Two Invariants

- Local-first development.
- Modular monolith for v0.
- Multi-tenancy from the first migration.
- Evidence and provenance attached to every external datum.
- Provider-neutral model gateway.
- Tool gateway for external actions.
- Paid APIs, paid models, infrastructure upgrades, storage upgrades, and overages disabled by default.
- Initial cash reserve is USD 20 and may only be spent intentionally by a human after a documented blocker.

## Current Phase

Phase 3: Atlas and Terra real-world context foundation.

The current backend foundation includes typed domain dataclasses, a SQL migration, and a SQLite-backed repository/test harness for tenant isolation. PostgreSQL remains the preferred Docker-backed development database once Docker Desktop is running.

Phase 2 adds deterministic mock provider/tool execution so cost, quota, permission, tenant, egress, provenance, cache, audit, and ledger controls can be proven before live Atlas/Terra adapters are introduced.

Phase 3 adds the first context engine:

```text
Location -> Atlas -> GeoContext -> Terra -> EnvironmentalSnapshot
```

This path uses zero model calls and remains fixture-tested by default.

## Local Commands

Windows-friendly commands:

```powershell
npm run check
npm run test
npm run lint
npm run eval
```

Unix-like convenience commands are mirrored in `Makefile`.

Docker is installed on the inspected machine, but Docker Desktop was not running during initial validation.

## Phase 1 Domain Boundary

GAIA's core domain is standalone. GreensWrld or other Cillian application schemas integrate later through adapters and mappings.

Authentication is provider-neutral. Local development may use deterministic development identities for tests, but development authentication is not production authentication. Authorization and tenancy remain GAIA-owned.

## Phase 2 Tool Boundary

Provider-backed calls must pass the GAIA Tool Gateway. A tool receives `ToolExecutionContext`, never global tenant state. The gateway enforces provider enabled state, Cost Firewall, quota policy, permissions, data egress, provenance capture, audit events, and usage ledger records.

No paid provider can execute automatically. Credentials do not authorize spend.

## Phase 3 Context Boundary

Atlas resolves normalized geography and zone containment. Terra compiles environmental context from normalized provider outputs and deterministic calculations. Provider-specific JSON does not appear in domain objects or API boundary responses.
