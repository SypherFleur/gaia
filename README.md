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

Phase 1: identity, tenancy, and canonical core domain foundation.

The current backend foundation includes typed domain dataclasses, a SQL migration, and a SQLite-backed repository/test harness for tenant isolation. PostgreSQL remains the preferred Docker-backed development database once Docker Desktop is running.

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
