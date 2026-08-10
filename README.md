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

Phase 0: repository constitution, comprehension, decisions, local environment validation, and reversible scaffolding.

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

