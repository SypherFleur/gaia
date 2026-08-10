# COMPREHENSION REPORT

Protocol Two status: initial interrogation complete.

Date: 2026-08-10

Repository inspected: `C:\Users\Jason\Documents\Codex\2026-08-10\sites-plugin-sites-openai-bundled-create`

GAIA repository root created: `C:\Users\Jason\Documents\Codex\2026-08-10\sites-plugin-sites-openai-bundled-create\gaia`

## 1. Governing Understanding

`GAIA_MASTER_BUILD_PLAN.md` is the governing build constitution for GAIA. It is not a loose brief. Implementation must preserve provenance, tenant isolation, model replaceability, multimodality, sovereign deployment capability, and the Cost Firewall from the first commit.

GAIA is a multimodal agricultural intelligence and guidance platform for growers, gardeners, farms, educators, extension agents, universities, research groups, NGOs, governments, and sovereign or regulated organizations. It combines model reasoning with structured agricultural data, plant knowledge, environmental context, soil and water context, geospatial jurisdiction, plant-health evidence, biosecurity rules, economic context, season planning, literature, community knowledge, plant/farm history, future BioCube telemetry, action tracking, and outcome learning.

GAIA is not a one-model chatbot. It is not a foundation-model training project, medical/veterinary diagnostic system, pesticide-prescription authority, legal compliance guarantee, commodity trading platform, autonomous farm controller, certified federal-compliance SaaS, replacement for extension professionals, completed global regulation database, microservice architecture, or paid-API-heavy demo.

The primary product object is `GuidancePlan`, not a chat message. Chat is one interface over that object. Future clients such as GreensWrld, BioCube, research dashboards, government systems, APIs, and field devices should consume the same structured object.

## 2. Architecture Understanding

GAIA v0 should be a modular monolith with explicit package boundaries. The internal boundaries must be clean enough for future extraction, but microservices are rejected for v0 unless scaling, security, isolation, or ownership requirements prove they are necessary.

The high-level flow is:

1. UI receives chat, media, location, plant, source, plan, calendar, or map interactions.
2. API/streaming boundary sends requests to the GAIA Orchestrator.
3. Authentication, organization, workspace, permissions, and risk are evaluated first.
4. The orchestrator classifies intent and checks whether location, regulation, deterministic tools, or model reasoning are needed.
5. Context Engine gathers relevant outputs from Terra, Atlas, Sentinel, Botanist, Scholar, Mercator, Season, Luna, and Vision.
6. Tool Gateway controls external tool calls by risk, permissions, schemas, and cost policy.
7. Model Gateway selects a provider by policy only when reasoning is needed.
8. Evidence/provenance validation happens before a `GuidancePlan` is emitted.
9. Human-facing response renders recommendation, actions, timing, confidence, sources, warnings, and follow-up.

The persistence layer starts with PostgreSQL through Docker when available, with SQLite as a constrained local fallback. pgvector is preferred only if vectors are needed with PostgreSQL. A dedicated graph database is deferred.

## 3. GuidancePlan Architecture

A user request becomes a `GuidancePlan` through deterministic routing before model reasoning. A simple deterministic lookup, such as "What county am I in?" or "What is tomorrow's low?", should not require a large model. A complex plant-health or planning request compiles evidence from multiple context modules and may use a model to synthesize, but not to invent sources.

A `GuidancePlan` must contain situation, recommendation, actions, timing, resources, geographic context, environmental context, regulatory constraints, evidence, uncertainty, risks, measurements, follow-up, and provenance. It links to `GeoContext`, `EnvironmentalSnapshot`, `EvidenceClaim`, `ModelRun`, and `ProvenanceBundle` records so the answer can be audited and reproduced later.

## 4. Multimodal and Vision Requirements

Vision is mandatory in the architecture and should be exposed in the MVP through image upload/camera capture. The schema must support image now and audio/video later, but audio and video UI are deferred.

The Vision workflow is not a single-label classifier. It must check quality, metadata/EXIF policy, plant/species candidates, plant part, visible symptoms, visual localization where available, environmental context, plant history, crop stage, differential diagnosis, confidence, and next observations.

GAIA must not make high-confidence disease diagnoses solely from an image classifier label. Poor images should trigger a request for better evidence. Ambiguous species candidates should trigger discriminating questions. High-risk disease, pesticide, or regulated action workflows require authoritative evidence and safety boundaries.

Institutional deployments must be able to disable cloud vision providers. Research deployments should optionally retain structured image metadata such as capture time, authorized location, plant ID, growth stage, device metadata if permitted, lighting quality, image quality score, model version, predictions, and researcher verification.

## 5. Specialist Modules

Terra is environmental intelligence. It owns weather, climate, solar radiation, photoperiod, drought, soil survey context, water context, growing degree calculations, freeze/heat context, and environmental normalization. Terra outputs `EnvironmentalSnapshot` and must separate current observation, forecast, historical climate, climatology, modeled regional data, and direct sensor data.

Atlas is the geospatial and jurisdiction resolver. It normalizes coordinates, resolves country/state/county/district/FIPS/admin IDs, watershed, climate zones, regulatory areas, and jurisdiction hierarchy. Atlas is required before location-sensitive regulatory guidance.

Sentinel is biosecurity and regulation. It handles domestic plant movement, quarantine zones, regulated articles, phytosanitary requirements, treatment/inspection requirements, pest/disease reporting guidance, and permit references. It must use authoritative sources first, attach retrieval timestamps, expire regulatory caches, and return `unresolved` when current verification is required but unavailable.

Botanist is plant intelligence. It handles taxonomy, crop profiles, plant characteristics, cultivar context, growth stage, germplasm discovery, biological constraints, and pest/disease candidate relationships. Structured biological data is preferred before RAG.

Scholar is research and evidence. It retrieves and synthesizes peer-reviewed literature, government guidance, extension material, community experience, experimental signals, contradictory evidence, study metadata, and evidence grades. It must respect copyright and source licenses.

Mercator is economics and supply chain. It handles crop production statistics, prices, market reports, county/regional economic context, structural commodity flow, and regional supply context. It must attach data dates and distinguish live market reports from historical or structural datasets. It must not provide investment advice.

Season is agricultural planning. It reasons about planting windows, task scheduling, crop calendars, frost and heat windows, phenology, growing degree days, forecast-aware adjustments, and calendar export. It must distinguish long-range climate planning from near-term forecasts and version plan revisions.

Luna is experimental astronomical context. It may calculate moon phase, illumination, moonrise/moonset, and optional correlation tracking. Lunar signals must be labeled experimental and may not override high-confidence agronomic evidence.

Vision is multimodal perception. It handles image-first MVP workflows and future document image, audio, and video inputs.

BioCube is future sensor/actuator integration. Its adapter interface can be designed, but actuation requires separate authentication, authorization, safety constraints, audits, failsafes, and human approval. General chat must never directly operate physical infrastructure.

## 6. Provenance and Evidence Requirements

Every external datum must be traceable through a provider result envelope containing value, unit, geographic scope, observed/valid/retrieved timestamps, provider, external record ID, source URL, license, attribution, freshness class, and confidence.

Evidence is represented through `EvidenceClaim` objects with evidence grade A-E, confidence, supporting source records, contradictory sources, and generated timestamp. The model may phrase a recommendation, but it may not fabricate evidence objects. Users must be able to ask why GAIA recommended something and receive an answer from persisted provenance rather than post-hoc invention.

Institutional/research use requires exportable `ProvenanceBundle` records containing source IDs, timestamps, observations, model/version, prompt/harness version, tool calls, relevant calculations, and evidence citations. Hidden chain-of-thought is not exposed.

## 7. Deployment Goals

GAIA Local is for development, testing, demos, and private use. It should run with Docker Compose, local database, local object storage, local model endpoint, and no paid APIs.

GAIA Public is for growers and eventual public alpha. It is multi-tenant, Cillian-managed, hard-rate-limited, free-tier-first, and optionally uses hosted inference only behind the Cost Firewall.

GAIA Institution is for universities, extension programs, research teams, NGOs, and enterprise agriculture. It needs organization workspaces, researcher roles, datasets, shared knowledge bases, reproducibility, retention controls, exports, and institution-specific tools/sources.

GAIA Sovereign is for governments and regulated organizations. It must support self-hosted or customer-controlled cloud deployment, customer-controlled keys later, private model runtime, local/vector databases, no protected content sent to Cillian, configurable telemetry, audit export, and jurisdiction pack deployment. No compliance certification should be claimed until actually achieved.

## 8. Jurisdiction Packs

Jurisdiction packs are versioned adapter bundles with `resolve_zones`, `movement_rules`, `pest_alerts`, and `agriculture_sources` interfaces. A movement check may combine federal, origin, destination, and quarantine-specific packs. The first implementation defaults to U.S. federal plus Texas, with Florida and Singapore next unless overridden.

GAIA must never simplify plant movement to county difference alone. Regulatory source freshness, authority, applicable rule, checked timestamp, and unresolved caveats are required.

## 9. Google Calendar Integration

Calendar support belongs to Season and should be designed now but implemented after core Season unless reprioritized. It must use OAuth, never Google passwords. Initial policy: `calendar.read` optional, `calendar.create` requires user confirmation, `calendar.update` requires confirmation for meaningful changes, and `calendar.delete` requires explicit user action.

Weather changes may recommend rescheduling, but must not silently reschedule unless a future automation policy explicitly permits it. GAIA-created events should include task title, crop/plant, instructions, plan ID, reason, weather sensitivity, GAIA back-reference, optional reminder, and internal `Action.id` to external event mapping to prevent duplicates.

## 10. Model Gateway and Provider Independence

The Model Gateway is a provider-neutral abstraction. Providers expose capabilities for text, image, audio, video, tool use, structured output, context window, local/remote status, and cost class. Providers are selected by policy, not scattered conditional logic.

Selection order is deterministic/no model, local/small model, free hosted model, stronger local multimodal model, stronger hosted-free model, and paid model only if an administrator explicitly enables it in the future. Nemotron 3 Nano Omni is a benchmark candidate, not a dependency. GAIA domain objects, prompts, tools, and storage must not be hard-coded to Nemotron, OpenAI, Ollama, Cloudflare, NVIDIA, or any single runtime.

This is how the architecture remains model-provider independent: core domain types do not contain provider-native message types, prompt/harness versions are tracked separately, `ModelRun` records provider/model/version/cost metadata, and model adapters sit behind a stable `ModelProvider` protocol.

## 11. Cost Firewall and Budget Understanding

The financial constitution is absolute:

```text
TOTAL_INITIAL_CASH_BUDGET_USD = 20.00
TARGET_DEVELOPMENT_CASH_SPEND_USD = 0.00
TARGET_COMMITTED_MONTHLY_INFRASTRUCTURE_USD = 0.00
ALLOW_AUTOMATIC_PAID_MODEL_USAGE = false
ALLOW_AUTOMATIC_PAID_API_USAGE = false
ALLOW_AUTOMATIC_INFRASTRUCTURE_UPGRADE = false
ALLOW_AUTOMATIC_OVERAGE_BILLING = false
ALLOW_AUTOMATIC_STORAGE_UPGRADE = false
PAID_MODEL_FALLBACK_ENABLED = false
PAID_DATA_FALLBACK_ENABLED = false
RESERVE_CASH_USD = 20.00
```

The $20 reserve may only be spent intentionally by a human after a documented blocker exists.

Paid APIs/models must remain disabled by default because GAIA's first invariant is economic safety. Free quota exhaustion, provider unavailability, or model failure must result in cached results, deterministic computation, local databases, approved free sources, smaller free/local models, local inference, graceful degradation, or a clear unavailable-capacity message. It must never silently become a paid request.

Every provider needs `ProviderCostPolicy`, hard request/compute limits where relevant, `hardMonthlyUsd = 0` by default, `allowOverage = false`, and auditability by provider, user, organization, and feature.

## 12. Repository and Environment Inspection

Initial workspace contents before GAIA setup:

- `outputs/`
- `work/`
- no existing Git repository
- no existing GAIA codebase

Resolved setup action: created a new `gaia` monorepo directory and initialized Git inside it.

Machine inspection:

| Area | Result |
| --- | --- |
| OS | Microsoft Windows 11 Home, version 10.0.26200, build 26200, 64-bit |
| CPU | Intel Core Ultra 9 185H, 16 cores, 22 logical processors |
| RAM | 23.37 GB total visible memory, about 3.2 GB free at inspection time |
| GPU | Intel Arc Graphics plus NVIDIA GeForce RTX 3050 6GB Laptop GPU |
| VRAM | NVIDIA reports 6144 MiB total, 5504 MiB free via `nvidia-smi`; WMI reported 4 GB, so `nvidia-smi` is treated as more authoritative for NVIDIA VRAM |
| NVIDIA driver / compute | driver 566.07, compute capability 8.6 |
| Disk | C: drive about 1428.19 GB free |
| Docker | Docker CLI 28.0.4 and Compose v2.34.0 installed; Docker Desktop service stopped and Linux engine pipe unavailable |
| WSL | WSL2 default distribution is `docker-desktop` |
| Node | v22.14.0 |
| npm | 10.9.2 |
| Python | `python` resolves to 3.11.9; Python 3.13.3 is available through `py -3.13` |
| Git | 2.48.1.windows.1 |
| Ollama | 0.32.5 installed |
| Local Ollama models | `llava:latest` 4.7 GB and `llama3.1:latest` 4.9 GB |
| Missing local tools | `make`, `uv`, `poetry`, `pnpm`, and `bun` are not installed |
| Virtualization signal | `VirtualizationFirmwareEnabled` reported false; Docker/WSL validation needs attention |

Local multimodal inference feasibility:

- The machine can run small local models and already has Ollama plus `llava:latest`.
- The 6 GB NVIDIA VRAM budget is likely too constrained for a 30B multimodal model such as Nemotron 3 Nano Omni without aggressive quantization, CPU/RAM offload, or a different runtime strategy.
- Python 3.13 is available and satisfies the plan's Python 3.12+ preference when invoked explicitly with `py -3.13`.
- Docker Compose cannot be runtime-validated until Docker Desktop service/engine is running.

## 13. Contradictions, Risks, and Missing Prerequisites

Contradictions or mismatches:

- The plan prefers Python 3.12+, but the `python` command points to 3.11.9. Python 3.13.3 is available through `py -3.13`, so scripts should explicitly use that on this machine.
- The plan's local development target is `docker compose up`, but Docker Desktop is installed and stopped. The daemon is not reachable right now.
- The plan treats local multimodal inference as important, but the available 6 GB VRAM constrains model choices. Nemotron 3 Nano Omni should remain a benchmark candidate, not a default.
- `make` is not available on this Windows environment, so platform-neutral npm/Python/PowerShell scripts are needed in addition to a Makefile.

Missing prerequisites:

- First alpha domain/subdomain.
- Authentication provider or identity constraints used by Cillian Industries.
- Google OAuth client credentials and redirect origin, when Calendar is implemented.
- Optional provider API keys: USDA NASS, USDA AMS, Pl@ntNet, and future hosted model providers. These must remain optional and disabled by default.
- Docker Desktop service/engine availability.
- Any existing Cillian/GreensWrld schemas, brand components, or legal data-sharing constraints outside this workspace.

Security concerns:

- Tenant isolation must be enforced in every protected query from the first migration.
- Exact farm/location coordinates are sensitive and need privacy precision defaults.
- Institution/government data egress must be policy-controlled before remote models or cloud vision providers are allowed.
- OAuth tokens must never be logged and should be stored only through secure credential references.
- Attachment handling requires type/size validation, safe filenames, ownership metadata, malware/unsafe file review where appropriate, and SSRF-safe source fetches.
- Regulatory guidance must return `unresolved` when current verification is required and unavailable.

Licensing concerns:

- Public accessibility does not imply training, caching, redistribution, derivative-use, or commercial rights.
- Each source needs a licensing registry record with unknown rights represented as `unknown`, not `allowed`.
- Research retrieval must respect article rights and avoid storing or redistributing full text unless permitted.
- Pl@ntNet attribution, quota, and terms must be reviewed before adapter implementation.
- GBIF citation and data-use rules must be respected.
- Private institutional images and uploaded documents may not be used for global model improvement without explicit agreement.

Implementation risks:

- Broad implementation before auth, tenancy, provenance, and cost policy would create expensive rework.
- Regulations, weather, market, and research data are time-sensitive; stale caches must be visible and bounded.
- Model gateway shortcuts could accidentally couple GAIA to one provider.
- Agent frameworks must remain adapters and must not own GAIA memory, security, or cost semantics.
- Calendar writes, chemical guidance, movement checks, and future actuation all require explicit confirmation/risk controls.

## 14. Proposed Implementation Order

Proceed in Protocol Two sequence:

1. Phase 0 / Commit 1: repository constitution, README, decisions, ADRs, dev scripts, Docker scaffold, lint/test/eval bootstrap, and local environment checks.
2. Commit 2: domain models, database, migrations, and tenancy tests.
3. Commit 3: provider registry, Cost Firewall, provenance envelope, and cache abstraction.
4. Commit 4: Atlas location/geospatial foundation.
5. Commit 5: Terra NWS, NASA POWER, and soil adapter foundation.
6. Commit 6: Model Gateway with local provider and structured output.
7. Commit 7: conversation plus `GuidancePlan` API.
8. Commit 8: web UI chat, sources, and location.
9. Commit 9: plant workspace.
10. Commit 10: vision image pipeline.

Do not implement multiple specialist modules simultaneously. Stop any portion where an unresolved architecture question would cause rework.

