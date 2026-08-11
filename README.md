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

Phase 8: Sentinel Biosecurity, Regulation, and Plant Movement Intelligence.

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

## Phase 6 Vision And Multimodal Plant Perception

Vision adds provider-neutral image analysis:

- `VisionProvider`, `VisionRequest`, `VisionResponse`, and `VisionCapabilities` isolate GAIA from any one local or remote vision provider.
- Local LLaVA through Ollama is available for development smoke tests; automated CI uses deterministic fixtures and does not require GPU, Ollama, live APIs, or large downloads.
- Pl@ntNet has an adapter boundary and fixtures. A Pl@ntNet key is optional and never required to boot or test GAIA.
- Visual observations and visual hypotheses are separate. Vision output is not a confirmed plant-health diagnosis.
- Vision calls pass through the Tool Gateway, Cost Firewall, quota checks, egress policy, cache, audit, and provenance capture.
- Plant Workspace observations keep visible facts separate from GAIA hypotheses.

Optional local LLaVA smoke:

```powershell
$env:GAIA_RUN_LLAVA_SMOKE='1'
$env:GAIA_LLAVA_MODEL='llava:latest'
py -3.13 -m unittest tests.phase6.test_llava_vision_smoke
```

## Phase 7 Scholar Research And Evidence Intelligence

Scholar adds query-driven research retrieval and evidence synthesis:

- `ResearchProvider`, `ResearchSearchRequest`, `ResearchSearchResponse`, `ResearchFetchRequest`, and `ResearchDocument` isolate GAIA from Europe PMC-specific shapes.
- Europe PMC is the first live-capable research adapter and is fixture-tested by default.
- `ResearchWork`, `ResearchClaim`, `EvidenceSynthesis`, research collections, and annotations preserve publication identity, evidence direction, study type, applicability, provenance, and tenant boundaries.
- Model-generated citations are rejected unless they match retrieved work IDs.
- Retrieved abstracts and paper text are untrusted data and cannot change system, tool, privacy, citation, or cost policy.
- Contradictory research remains visible; Scholar does not flatten mixed evidence into false certainty.

Optional Europe PMC smoke:

```powershell
$env:GAIA_RUN_RESEARCH_SMOKE='1'
py -3.13 -m unittest tests.phase7.test_europe_pmc_smoke
```

## Phase 8 Sentinel Regulatory Intelligence

Sentinel adds deterministic plant movement decision support:

- Provider-neutral `RegulationProvider` boundary.
- `MovementRequest`, `SentinelContext`, and `MovementDecision` domain flow.
- Fixture-backed `us_federal` and `us_tx` jurisdiction packs with APHIS and Texas Agriculture source provenance.
- Fail-closed freshness and conflict handling for current regulatory checks.
- Atlas zone/admin context integration without leaking exact private coordinates to remote providers.
- Vision regulated-pest and Genesys shipping questions route to Sentinel rather than becoming diagnoses or legal conclusions.

Optional APHIS/Texas read-only smoke:

```powershell
$env:GAIA_RUN_SENTINEL_SMOKE='1'
py -3.13 -m unittest tests.phase8.test_sentinel_smoke
```
