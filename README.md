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

Phase 5: Botanist and Plant Workspace.

The current backend foundation includes typed domain dataclasses, a SQL migration, and a SQLite-backed repository/test harness for tenant isolation. PostgreSQL remains the preferred Docker-backed development database once Docker Desktop is running.

Phase 2 adds deterministic mock provider/tool execution so cost, quota, permission, tenant, egress, provenance, cache, audit, and ledger controls can be proven before live Atlas/Terra adapters are introduced.

Phase 3 adds the first context engine:

```text
Location -> Atlas -> GeoContext -> Terra -> EnvironmentalSnapshot
```

This path uses zero model calls and remains fixture-tested by default.

Phase 4 adds the first chat/reasoning loop:

```text
Chat -> GAIA Orchestrator -> deterministic route OR ContextBundle -> Model Gateway -> validated GuidancePlan
```

Geography and environment questions still produce zero ModelRuns. Reasoning routes require `model.chat`, use an approved local model provider, validate structured output before persistence, and attach trusted provenance from the compiled context rather than from model-generated citations.

## Local Commands

Windows-friendly commands:

```powershell
npm run check
npm run test
npm run lint
npm run eval
```

Optional local Ollama smoke:

```powershell
$env:GAIA_RUN_OLLAMA_SMOKE='1'
$env:GAIA_OLLAMA_MODEL='llama3.1:latest'
py -3.13 -m unittest tests.phase4.test_ollama_smoke
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

## Phase 4 Chat And Model Boundary

The Model Gateway owns provider-neutral inference. Local Ollama is an adapter, not a dependency. The orchestrator classifies requests before selecting any model, persists conversations/messages in GAIA tables, and refuses to persist malformed GuidancePlans.

Model-generated source IDs and citations are rejected. Source records are attached by GAIA from trusted Atlas/Terra context provenance.

## Phase 5 Botanist And Plant Workspace

Botanist adds canonical plant intelligence:

- GBIF-backed taxonomy and synonym resolution through the Tool Gateway.
- Genesys PGR germplasm discovery through the Tool Gateway.
- Source-backed `PlantProfile` records with field provenance and conflicts.
- User-owned plant records with cultivar, lifecycle stage, growing method, notes, tags, location, and archived/deleted state.
- Observation timelines that keep observed facts separate from GAIA hypotheses.
- Plant-aware chat context for “Ask GAIA about this plant.”

Taxonomy lookup, plant retrieval, observation retrieval, germplasm lookup, and Botanist context generation do not require model inference. Reasoning still records a ModelRun only when the local model is used.
