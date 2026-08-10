# GAIA_MASTER_BUILD_PLAN.md

> **Protocol Two — Codex Build Constitution**
>
> Project: **GAIA — Agricultural Intelligence & Guidance System**
>
> Company: **Cillian Industries**
>
> Status: **Architecture-approved draft for Codex interrogation before implementation**
>
> Date baseline: **2026-08-10**
>
> Initial cash budget: **USD $20 total**
>
> Default committed monthly infrastructure spend: **USD $0**
>
> Primary rule: **No automatic paid API, model, storage, database, or infrastructure overages.**

---

# 0. How Codex Must Use This Document

This is not a loose product brief. It is the governing build specification for GAIA.

Before writing major production code, Codex MUST:

1. Read this document in full.
2. Inspect the repository in full if a repository already exists.
3. Produce a short `COMPREHENSION_REPORT.md` containing:
   - its understanding of GAIA,
   - the proposed implementation order,
   - conflicts between this plan and the existing repository,
   - assumptions it would otherwise make,
   - budget or security risks,
   - missing credentials or external prerequisites,
   - data-source licensing concerns,
   - model/hardware feasibility concerns.
4. Produce `OPEN_QUESTIONS.md` containing only questions that materially affect architecture, privacy, cost, user experience, or correctness.
5. Ask those questions before making irreversible architectural choices.
6. Record answered questions in `DECISIONS.md`.
7. Do not silently invent business rules.
8. Do not silently enable a paid service.
9. Do not weaken provenance, access control, or cost limits to make a feature easier to implement.
10. After questions are resolved, build in the phase order defined in this document unless the repository itself creates a dependency requiring a different order.

Codex MAY immediately perform safe, reversible setup work such as repository inspection, dependency auditing, documentation scaffolding, test setup, formatting configuration, Docker configuration, and local environment validation.

Codex MUST NOT begin broad implementation if it discovers a contradiction that would cause a major rewrite.

### Required Codex response before implementation

Codex should be able to explain, in its own words:

- what GAIA is,
- what GAIA is not,
- how a user request becomes a Guidance Plan,
- how location affects the answer,
- how evidence is attached to a claim,
- how a paid request is prevented,
- how model providers can be swapped,
- how an image diagnosis differs from a deterministic data lookup,
- how a university tenant differs from a public grower tenant,
- how a sovereign deployment can run without Cillian Industries receiving its protected data,
- what happens when a free API quota is exhausted,
- which features are intentionally deferred.

If Codex cannot explain those correctly, it has not understood the project.

---

# 1. Product Definition

GAIA is a **multimodal agricultural intelligence and guidance platform**.

It is not merely a conversational LLM and it is not a one-model product.

GAIA combines:

- multimodal model reasoning,
- agricultural data,
- plant and crop knowledge,
- environmental context,
- soil and water data,
- geospatial jurisdiction,
- plant-health evidence,
- biosecurity and movement restrictions,
- economic and supply-chain context,
- seasonal planning,
- scientific literature,
- community knowledge,
- user-specific plant/farm history,
- later BioCube sensor telemetry,
- action tracking,
- outcome learning.

The product is designed to serve, over time:

- individual growers,
- gardeners,
- farmers,
- community gardens,
- agricultural educators,
- extension agents,
- universities,
- agricultural research groups,
- institutional agriculture programs,
- NGOs,
- governments,
- sovereign or regulated organizations.

GAIA must scale conceptually from an individual plant to a research institution without replacing the core architecture.

---

# 2. Product Promise

GAIA does not sell “tokens.”

GAIA should convert questions and observations into **actionable, evidence-aware agricultural outcomes**.

The primary product object is not a chat message.

The primary product object is a:

`GuidancePlan`

A Guidance Plan contains:

- situation,
- recommendation,
- actions,
- timing,
- materials/resources,
- geographic context,
- environmental context,
- regulatory constraints,
- evidence,
- uncertainty,
- risks,
- measurements,
- follow-up,
- provenance.

Chat is the human interface over this object.

Other future clients — GreensWrld, BioCube, research dashboards, government systems, APIs, field devices — should be able to consume the same underlying object.

---

# 3. Non-Goals for the First Build

GAIA v0 is NOT:

- a new frontier foundation model trained from scratch,
- a medical or veterinary diagnostic system,
- a pesticide-prescription authority,
- a legal compliance guarantee,
- a commodity trading platform,
- a fully autonomous farm controller,
- a federal-compliance-certified SaaS,
- a replacement for agricultural extension professionals,
- a global regulation database completed on day one,
- a microservice architecture,
- a paid-API-heavy demo.

The architecture must leave room for these domains where appropriate, but the first implementation must stay narrow enough to be built and operated under the budget constraint.

---

# 4. Financial Constitution

The first technical invariant is economic.

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

The $20 reserve may only be spent intentionally, by a human, after a documented blocker exists.

### Cost fallback order

When a quota, model, data source, or hosted service becomes unavailable:

1. use cached result if valid;
2. use deterministic local computation;
3. use a local database;
4. use another approved free source;
5. use a smaller approved free/local model;
6. use local inference;
7. degrade the feature gracefully;
8. tell the user that advanced capacity is temporarily unavailable.

Do NOT automatically convert the request into a paid request.

### Cost ledger

Every external provider must implement:

```ts
interface ProviderCostPolicy {
  providerId: string;
  billingClass: "free" | "local" | "manual-paid";
  hardDailyRequests?: number;
  hardDailyComputeUnits?: number;
  hardMonthlyUsd: number; // 0 by default
  allowOverage: false;
  quotaReset?: string;
}
```

Every model/tool invocation must be eligible for audit by provider, user, organization, and feature.

---

# 5. Feasibility Baseline

The project is feasible if GAIA is treated as a **system**, not as a requirement to train a foundation model.

Current relevant model feasibility:

- NVIDIA Nemotron 3 Nano Omni is a 30B-A3B multimodal model designed to handle text, image, audio, and video in a unified model architecture.
- It is a candidate, not a hard dependency.
- GAIA MUST use a model abstraction so another multimodal model can be swapped in.
- Actual local performance depends on the development machine and quantization/runtime support.
- Codex MUST inspect available RAM/VRAM/CPU/GPU before selecting a default local model configuration.

Official reference:
- https://developer.nvidia.com/blog/nvidia-nemotron-3-nano-omni-powers-multimodal-agent-reasoning-in-a-single-efficient-open-model
- https://developer.nvidia.com/topics/ai/nemotron

Hosted-free feasibility:
- Cloudflare Workers AI currently provides a daily free allocation, with usage above the free allocation unavailable on the Workers Free plan unless upgraded.
- This is acceptable for GAIA because failure is preferable to surprise billing.

Official reference:
- https://developers.cloudflare.com/workers-ai/platform/pricing/

This document DOES NOT require Cloudflare. The architecture must be deployable locally first.

---

# 6. Deployment Profiles

GAIA must support the following conceptual deployment profiles from one codebase.

## 6.1 GAIA Local

Purpose:
- development,
- testing,
- demos,
- private use.

Characteristics:
- Docker Compose,
- local database,
- local object storage,
- local model endpoint,
- no paid APIs required.

## 6.2 GAIA Public

Purpose:
- growers,
- public alpha,
- consumer subscriptions later.

Characteristics:
- multi-tenant,
- Cillian-managed infrastructure,
- hard rate limits,
- free-tier-first infrastructure,
- optional hosted inference constrained by Cost Firewall.

## 6.3 GAIA Institution

Purpose:
- universities,
- extension programs,
- research teams,
- NGOs,
- enterprise agriculture.

Characteristics:
- organization workspaces,
- researcher roles,
- datasets,
- shared knowledge bases,
- reproducibility,
- configurable retention,
- exportable research records,
- institution-specific tools and sources.

## 6.4 GAIA Sovereign

Purpose:
- governments,
- regulated institutions,
- organizations with data-residency requirements.

Characteristics:
- self-hosted or customer-controlled cloud,
- customer-controlled keys,
- private model runtime,
- local/vector databases,
- no requirement to send protected content to Cillian,
- configurable telemetry,
- audit export,
- jurisdiction pack deployment.

Do not claim compliance certifications until achieved.

---

# 7. Architecture Style

For v0, implement GAIA as a **modular monolith** with explicit package boundaries.

Do not create microservices without a demonstrated scaling, security, isolation, or ownership requirement.

Reasons:

- simpler development,
- zero-cost local operation,
- fewer deployables,
- easier debugging,
- simpler transactional boundaries,
- easier testing,
- lower latency,
- easier Codex comprehension.

Internal interfaces MUST make future extraction possible.

---

# 8. High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                          GAIA UI                             │
│ Chat · Vision · Sources · Plants · Plans · Calendar · Maps │
└───────────────────────────────┬──────────────────────────────┘
                                │
                     Streaming/API Boundary
                                │
┌───────────────────────────────▼──────────────────────────────┐
│                    GAIA ORCHESTRATOR                         │
│ intent · safety · route · compile context · produce plan    │
├──────────────────────────────────────────────────────────────┤
│ Context Engine             │ Tool Gateway │ Model Gateway   │
├────────────────────────────┼──────────────┼─────────────────┤
│ Terra                      │ Weather      │ Local model     │
│ Atlas                      │ Soil         │ Hosted free     │
│ Sentinel                   │ Water        │ Optional manual │
│ Botanist                   │ Research     │ provider        │
│ Scholar                    │ Market       │                 │
│ Mercator                   │ Vision       │                 │
│ Season                     │ Calendar     │                 │
│ Luna Context               │ Geospatial   │                 │
├──────────────────────────────────────────────────────────────┤
│ Evidence · Provenance · Permissions · Cost Firewall · Audit │
├──────────────────────────────────────────────────────────────┤
│ PostgreSQL/SQLite · pgvector(optional) · Object storage     │
└──────────────────────────────────────────────────────────────┘
```

---

# 9. Recommended Initial Technology Stack

Codex may challenge a choice, but it must explain why.

## Frontend

Preferred:
- TypeScript
- React
- Next.js or an equivalent React framework
- responsive web app
- PWA-friendly
- accessible keyboard navigation
- mobile camera capture

## Backend

Preferred:
- Python 3.12+
- FastAPI
- Pydantic v2
- async HTTP clients
- SQLAlchemy 2 or equivalent typed ORM
- Alembic migrations

Rationale:
Agricultural data, geospatial tooling, scientific processing, ML integration, and future research workloads strongly favor Python.

## Database

Development:
- PostgreSQL when available through Docker,
- SQLite fallback for extremely constrained local development.

Production:
- PostgreSQL-compatible storage preferred.

Vector:
- pgvector preferred when PostgreSQL is used.
- Do not introduce a separate vector database for v0.

## Cache

Start:
- application cache + database-backed cache tables.

Later:
- Redis-compatible cache only if measurements justify it.

## Object storage

Development:
- local filesystem or MinIO.

Hosted:
- R2/S3-compatible object storage.

## Model runtime

Implement OpenAI-compatible or provider-neutral adapters.

Candidate local runtimes:
- llama.cpp where model support is sufficient,
- Ollama for easy local development,
- vLLM or NVIDIA runtimes when hardware and model compatibility justify them.

The rest of GAIA must not depend directly on one runtime.

---

# 10. Repository Layout

Recommended monorepo:

```text
gaia/
├── README.md
├── GAIA_MASTER_BUILD_PLAN.md
├── COMPREHENSION_REPORT.md
├── OPEN_QUESTIONS.md
├── DECISIONS.md
├── CHANGELOG.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
│
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── lib/
│   │   └── tests/
│   │
│   └── api/
│       ├── gaia_api/
│       └── tests/
│
├── packages/
│   ├── domain/
│   ├── orchestration/
│   ├── context/
│   ├── models/
│   ├── tools/
│   ├── evidence/
│   ├── provenance/
│   ├── geospatial/
│   ├── permissions/
│   ├── cost/
│   ├── evals/
│   └── common/
│
├── adapters/
│   ├── weather/
│   ├── climate/
│   ├── soil/
│   ├── water/
│   ├── plants/
│   ├── germplasm/
│   ├── biodiversity/
│   ├── regulation/
│   ├── economics/
│   ├── research/
│   ├── vision/
│   ├── calendar/
│   └── models/
│
├── jurisdiction_packs/
│   ├── us_federal/
│   ├── us_tx/
│   ├── us_fl/
│   └── sg/
│
├── data/
│   ├── seed/
│   ├── fixtures/
│   ├── evals/
│   └── licenses/
│
├── scripts/
│   ├── bootstrap/
│   ├── ingest/
│   ├── sync/
│   └── eval/
│
├── migrations/
├── docs/
│   ├── architecture/
│   ├── data-sources/
│   ├── security/
│   ├── deployment/
│   ├── research/
│   └── adr/
│
└── tests/
    ├── integration/
    ├── contract/
    ├── security/
    ├── cost/
    └── evals/
```

---

# 11. Core Domain Model

The database must be multi-tenant from the first migration.

## 11.1 Organization

```text
Organization
- id
- name
- slug
- type: personal | community | university | government | business | ngo
- deployment_mode
- default_country
- default_units
- data_retention_policy
- created_at
```

## 11.2 User

```text
User
- id
- external_auth_id
- display_name
- locale
- timezone
- default_units
- created_at
```

## 11.3 Membership

```text
Membership
- organization_id
- user_id
- role
- permissions[]
```

Initial roles:
- owner
- admin
- researcher
- extension_agent
- grower
- viewer

## 11.4 Workspace

```text
Workspace
- id
- organization_id
- name
- purpose
- default_location_id
- knowledge_policy
- created_at
```

A workspace may represent:
- a personal garden,
- farm,
- university project,
- research trial,
- greenhouse,
- extension program,
- government analysis environment.

## 11.5 Location

```text
Location
- id
- organization_id
- label
- latitude
- longitude
- elevation_m
- accuracy_m
- privacy_precision
- timezone
- country_code
- admin1
- admin2
- county_fips
- created_at
```

Exact location must be access-controlled.

## 11.6 GeoContext

Generated, versioned context.

```text
GeoContext
- location_id
- generated_at
- country
- state_or_region
- county_or_district
- county_fips
- hardiness_zone
- ecoregion
- watershed
- climate_zone
- regulatory_zones[]
- quarantine_zones[]
- pest_zones[]
- economic_regions[]
- source_records[]
```

## 11.7 PlantEntity

Canonical biological entity.

```text
PlantEntity
- id
- scientific_name
- canonical_taxon_id
- common_names[]
- family
- genus
- species
- subspecies
- cultivar_optional
- crop_group
- source_ids
```

## 11.8 UserPlant

```text
UserPlant
- id
- workspace_id
- plant_entity_id
- nickname
- cultivar
- planted_at
- acquired_at
- lifecycle_stage
- location_id
- container_or_bed
- status
```

## 11.9 Observation

```text
Observation
- id
- user_plant_id
- observed_at
- author_id
- text
- images[]
- audio[]
- video[]
- measurements{}
- weather_snapshot_id
- source: user | sensor | imported
```

## 11.10 EnvironmentalSnapshot

```text
EnvironmentalSnapshot
- id
- location_id
- observed_or_valid_at
- retrieved_at
- temperature
- humidity
- precipitation
- wind
- pressure
- solar_radiation
- photoperiod
- soil_context{}
- soil_moisture_context{}
- drought_context{}
- water_context{}
- source_records[]
```

## 11.11 EvidenceClaim

```text
EvidenceClaim
- id
- claim_text
- evidence_grade: A | B | C | D | E
- confidence: 0..1
- source_records[]
- contradictory_sources[]
- generated_at
```

Evidence grades:

- A: direct measurement/observation plus authoritative current data
- B: authoritative government source or strong peer-reviewed evidence
- C: established agronomic/horticultural reference
- D: community or grower experiential knowledge
- E: experimental hypothesis, preliminary evidence, or traditional practice

## 11.12 GuidancePlan

```text
GuidancePlan
- id
- conversation_id
- workspace_id
- subject
- situation
- recommendations[]
- actions[]
- timing[]
- resources[]
- evidence_claims[]
- risks[]
- uncertainty
- measurements_to_take[]
- follow_up[]
- geo_context_id
- environmental_snapshot_id
- created_at
- model_run_ids[]
- provenance_bundle_id
```

## 11.13 Action

```text
Action
- id
- guidance_plan_id
- title
- instructions
- earliest_at
- preferred_at
- deadline
- dependencies[]
- weather_sensitive
- user_confirmation_required
- completion_status
- completed_at
```

## 11.14 Outcome

```text
Outcome
- id
- action_id
- user_plant_id
- observed_at
- result
- measurements{}
- user_rating
- attachments[]
```

This is the foundation of the future GAIA Outcome Graph.

## 11.15 RegulationRule

```text
RegulationRule
- id
- jurisdiction_pack
- authority
- authority_level
- subject_type
- regulated_article
- pest_or_disease
- geometry_or_area_reference
- origin_scope
- destination_scope
- conditions[]
- permit_requirements[]
- treatment_requirements[]
- effective_from
- effective_to
- source_record_id
- last_verified_at
```

## 11.16 MovementCheck

```text
MovementCheck
- id
- origin_geo_context
- destination_geo_context
- article
- species
- plant_part
- soil_attached
- purpose
- planned_date
- status: allowed | conditional | restricted | unresolved
- applicable_rules[]
- caveats[]
- source_records[]
- checked_at
```

Legal wording MUST communicate that GAIA provides guidance based on retrieved authoritative sources, not a legal guarantee.

## 11.17 SeasonPlan

```text
SeasonPlan
- id
- workspace_id
- crop_or_plant_ids[]
- objective
- location_id
- date_range
- tasks[]
- climate_basis
- forecast_basis
- regulatory_constraints[]
- market_context[]
- generated_at
```

## 11.18 CalendarBinding

```text
CalendarBinding
- id
- organization_id
- user_id
- provider
- external_calendar_id
- encrypted_credential_reference
- scopes[]
- created_at
```

Never store raw OAuth tokens in logs.

## 11.19 SourceRecord

```text
SourceRecord
- id
- provider
- source_type
- canonical_url
- external_record_id
- title
- authority
- retrieved_at
- observed_at
- valid_from
- valid_to
- license
- attribution
- content_hash
- raw_snapshot_reference
```

## 11.20 ModelRun

```text
ModelRun
- id
- provider
- model
- model_version
- local_or_remote
- input_modalities[]
- input_tokens_or_units
- output_tokens_or_units
- elapsed_ms
- cost_usd
- tool_calls[]
- prompt_version
- created_at
```

---

# 12. GAIA Orchestrator

The orchestrator is the decision engine responsible for turning a request into the correct workflow.

It must NOT call a large model before determining whether a model is needed.

Required flow:

```text
request
  ↓
authentication / organization / permissions
  ↓
intent classification
  ↓
location relevance check
  ↓
risk / regulation relevance
  ↓
required deterministic tools
  ↓
context compilation
  ↓
model selection only if reasoning is needed
  ↓
evidence validation
  ↓
GuidancePlan
  ↓
human-facing response
```

### Routing examples

“What is tomorrow’s low temperature?”
- weather tool
- no LLM required except optional natural-language rendering.

“What USDA hardiness zone is this?”
- geospatial/hardiness lookup
- no large model.

“What can I plant this month?”
- Atlas + Terra + Botanist + Season
- lightweight reasoning.

“What is wrong with these leaves?”
- Vision + Terra + Botanist + Scholar where needed
- multimodal reasoning
- differential diagnosis.

“Can I move this citrus tree to another county?”
- Atlas + Sentinel
- current authoritative regulatory retrieval
- LLM only for synthesis, never as source of legal rule.

---

# 13. Context Engine and Specialist Modules

These are logical specialists. They do not all need separate LLM calls.

## 13.1 Terra — Environmental Intelligence

Responsibilities:
- weather,
- climate,
- solar radiation,
- photoperiod,
- drought,
- soil survey context,
- water context,
- growing degree calculations,
- freeze/heat context,
- environmental normalization.

Output:
`EnvironmentalSnapshot`

Terra must distinguish:
- current observation,
- forecast,
- historical climate,
- climatology,
- modeled regional data,
- direct sensor data.

Do not present modeled regional soil moisture as an exact root-zone sensor reading.

## 13.2 Atlas — Geospatial & Jurisdiction Resolver

Responsibilities:
- coordinate normalization,
- country/state/county/district resolution,
- FIPS/administrative identifiers,
- watershed,
- climate zones,
- regulatory area overlays,
- jurisdiction hierarchy.

Atlas is required before location-sensitive regulatory guidance.

## 13.3 Sentinel — Biosecurity & Regulation

Responsibilities:
- domestic plant movement,
- quarantine zones,
- regulated articles,
- phytosanitary requirements,
- treatment/inspection requirements,
- pest/disease reporting guidance,
- permit references.

Rules:
- authoritative sources first;
- regulation cache must have an expiration;
- high-risk answers must include retrieval timestamp;
- if boundaries or rules are ambiguous, answer `unresolved` and direct the user to the named authority rather than hallucinating.

APHIS has explicitly moved some quarantined-area and regulated-article lists to updateable web resources, which reinforces the need for current retrieval rather than frozen model memory.

Official references:
- https://www.aphis.usda.gov/plant-pests-diseases/aphis-streamlines-domestic-quarantines-certain-plant-pests
- https://www.aphis.usda.gov/plant-pests-diseases/fruit-flies/fruit-fly-quarantine-maps-descriptions
- https://www.aphis.usda.gov/plant-imports/regulated-pest-list

## 13.4 Botanist — Plant Intelligence

Responsibilities:
- taxonomy,
- crop profiles,
- plant characteristics,
- cultivar context,
- growth stage,
- germplasm discovery,
- biological constraints,
- pest/disease candidate relationships.

Botanist should prefer structured biological data before RAG.

## 13.5 Scholar — Research & Evidence

Responsibilities:
- peer-reviewed search,
- evidence synthesis,
- contradictory evidence,
- study metadata,
- research-grade citations,
- evidence grading.

Scholar must separate:
- peer-reviewed literature,
- government guidance,
- extension material,
- community experience,
- experimental signals.

It may retrieve papers but must respect copyright and source licenses.

## 13.6 Mercator — Economics & Supply Chain

Responsibilities:
- crop production statistics,
- prices,
- market reports,
- county/regional economic context,
- structural commodity flow,
- regional supply context.

Mercator MUST attach data dates.
Agricultural economics can be highly time-sensitive.

## 13.7 Season — Agricultural Planning

Responsibilities:
- what to plant,
- when to plant,
- task scheduling,
- crop calendars,
- frost-window reasoning,
- heat windows,
- phenology,
- growing degree days,
- forecast-aware task adjustments,
- calendar export.

Season must distinguish long-range planning from actual weather forecasting.

Planning confidence progression:

```text
90+ days    -> climate normals / historical distribution
30–90 days  -> seasonal/climatological context
7–14 days   -> forecast influence begins
0–7 days    -> high forecast influence
day-of      -> current conditions + local measurements
```

## 13.8 Luna — Experimental Astronomical Context

Luna is not a primary recommendation engine.

Responsibilities:
- moon phase,
- illumination,
- moonrise/moonset,
- optional experimental correlation tracking.

Rules:
- lunar signals must be labeled experimental unless sufficient crop-specific evidence exists;
- a lunar signal must not override high-confidence agronomic evidence;
- record it in outcome studies if users choose to investigate it.

## 13.9 Vision — Multimodal Perception

Vision accepts:
- images now,
- document images,
- later audio and video.

Pipeline:

```text
media
  ↓
quality checks
  ↓
metadata / EXIF policy
  ↓
plant/species candidates
  ↓
symptom candidates
  ↓
visual localization where available
  ↓
Terra / plant history / crop stage
  ↓
differential diagnosis
  ↓
confidence + next observation
```

Vision is NOT allowed to make a high-confidence diagnosis solely because the image classifier produced one label.

For disease questions, GAIA should generate ranked hypotheses and ask for discriminating observations when evidence is insufficient.

## 13.10 BioCube Adapter — Future

Not required for MVP.

Design interface now for later:
- temperature,
- humidity,
- water level,
- water flow,
- EC,
- pH,
- energy,
- nutrient measurements,
- camera feeds,
- actuator commands.

Actuator control MUST require a separate safety/permission architecture.

---

# 14. Model Gateway

Define:

```py
class ModelProvider(Protocol):
    async def capabilities(self) -> ModelCapabilities: ...
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
```

`ModelCapabilities` must advertise:
- text,
- image,
- audio,
- video,
- tool use,
- structured output,
- context window,
- local/remote,
- cost class.

Providers must be selected by policy, not scattered conditional statements.

Candidate adapters:
- local llama.cpp/OpenAI-compatible,
- Ollama,
- NVIDIA runtime,
- Cloudflare Workers AI,
- other providers only when intentionally configured.

### Model selection policy

Prefer:

1. deterministic tool / no model,
2. local/small model,
3. free hosted model,
4. stronger local multimodal model,
5. stronger hosted-free model,
6. paid model only if explicitly enabled by an administrator later.

### Primary multimodal candidate

Nemotron 3 Nano Omni should be benchmarked as a candidate for:
- image reasoning,
- document/image interpretation,
- multimodal subagent work,
- later audio/video.

Do NOT hard-code GAIA prompts, database objects, or tools to Nemotron-specific APIs.

---

# 15. Tool Gateway

All external actions pass through a common tool policy.

```ts
interface ToolDefinition {
  id: string;
  risk: "read" | "write" | "regulated" | "actuator";
  requiredPermissions: string[];
  costPolicy: ProviderCostPolicy;
  inputSchema: JsonSchema;
  outputSchema: JsonSchema;
}
```

### Tool classes

Read tools:
- weather,
- soil,
- water,
- geospatial,
- research,
- taxonomy,
- germplasm,
- market.

Write tools:
- calendar create/update,
- user notes,
- task completion,
- future institutional data writes.

Regulated tools:
- regulatory checks,
- phytosanitary workflows.

Actuator tools:
- future BioCube or farm automation.

LLMs must never bypass the Tool Gateway.

---

# 16. Google Calendar Integration

Season may integrate Google Calendar.

Use OAuth.
Do not ask users for Google passwords.

Official event creation:
- https://developers.google.com/workspace/calendar/api/guides/create-events

Initial permission policy:

```text
calendar.read        optional
calendar.create      user confirmation
calendar.update      user confirmation for meaningful changes
calendar.delete      explicit user action only
```

A weather change should produce:
“GAIA recommends moving this task.”

It should not silently reschedule unless the user later enables an automation policy.

### Calendar event metadata

GAIA-created events should include:
- task title,
- crop/plant,
- short instructions,
- plan ID,
- reason,
- weather sensitivity,
- link/back-reference to GAIA,
- optional reminder.

GAIA must maintain an internal mapping between `Action.id` and external calendar event ID to prevent duplicates.

---

# 17. Data Architecture: Structured vs Retrieval vs Live

Do not put all knowledge in a vector database.

## Structured relational data

Use for:
- users,
- organizations,
- plants,
- observations,
- soil profiles,
- time-series metadata,
- regulations,
- market snapshots,
- Guidance Plans,
- evidence,
- outcomes.

## Retrieval corpus / embeddings

Use for:
- extension documents,
- government manuals,
- scientific papers where allowed,
- crop guides,
- institutional documents,
- user-imported research libraries.

## Live tools

Use for:
- weather,
- alerts,
- current water,
- current quarantines,
- current market data,
- calendar.

## Object storage

Use for:
- photos,
- videos,
- documents,
- raw provider snapshots,
- exports.

---

# 18. Knowledge Graph Strategy

Do NOT introduce a dedicated graph database in v0 unless required.

Model graph relationships relationally first.

Core graph edges include:

```text
Plant -> Pest
Plant -> Disease
Plant -> Trait
Plant -> Cultivar
Plant -> Germplasm accession
Plant -> Soil requirement
Plant -> Climate requirement
Plant -> Regulation
Location -> Jurisdiction
Location -> Quarantine
Location -> Climate
Location -> Watershed
Action -> Plant
Action -> Recommendation
Recommendation -> Evidence
Recommendation -> Outcome
Outcome -> Environment
Market -> Commodity
Commodity -> Region
```

If graph queries later become a measurable bottleneck, evaluate a graph database then.

---

# 19. Provenance

Every external datum must be traceable.

Minimum provider result envelope:

```json
{
  "value": "...",
  "unit": "...",
  "geographic_scope": "...",
  "observed_at": "...",
  "valid_at": "...",
  "retrieved_at": "...",
  "provider": "...",
  "external_record_id": "...",
  "source_url": "...",
  "license": "...",
  "attribution": "...",
  "freshness_class": "...",
  "confidence": 0.0
}
```

A user must be able to ask:
“Why did GAIA recommend this?”

GAIA must be able to answer from persisted provenance, not invent a justification after the fact.

For institutional/research use, allow export of a `ProvenanceBundle` containing:
- data source identifiers,
- timestamps,
- input observations,
- model/version,
- prompt/harness version,
- tool calls,
- relevant calculations,
- evidence citations.

Do not expose hidden chain-of-thought. Preserve auditable inputs and decision evidence instead.

---

# 20. Data Source Registry

Each adapter needs a registry entry:

```text
provider
domain
authority
endpoint
auth_required
cost_class
quota
geographic_scope
temporal_scope
freshness
cache_ttl
fallback
license
training_rights
redistribution_rights
attribution
notes
```

Training rights must NEVER be inferred from public accessibility.

## 20.1 Weather — National Weather Service

Use for U.S. forecast and alert context.

Official:
- https://www.weather.gov/documentation/standards/services-web-api

Cache:
- short TTL appropriate to endpoint.

## 20.2 Climate/Solar — NASA POWER

Use for:
- solar,
- meteorological history,
- climatology,
- agricultural environmental context.

Hourly API provides data from 2001 to near-real-time.

Official:
- https://power.larc.nasa.gov/docs/services/api/
- https://power.larc.nasa.gov/docs/services/api/temporal/hourly/

Do not treat NASA POWER as field-level sensor data.

## 20.3 Soil — USDA NRCS Soil Data Access / SSURGO

Official soil survey information.

Official:
- https://sdmdataaccess.nrcs.usda.gov/
- https://sdmdataaccess.nrcs.usda.gov/WebServiceHelp.aspx

Important:
SSURGO is soil survey/property context.
It is NOT a live root-zone soil-moisture sensor.

Cache aggressively by area and source version.

## 20.4 Water — USGS

Use current USGS water API strategy.
Legacy WaterServices is scheduled for decommissioning in early 2027, so adapters must be written behind an interface and migration-aware.

Reference:
- https://waterservices.usgs.gov/
- future API family: https://api.waterdata.usgs.gov

Do not hard-code the legacy API deeply into GAIA.

## 20.5 USDA NASS Quick Stats

Use for official U.S. agricultural production statistics and Census of Agriculture context, including county-level data where published.

Official:
- https://www.nass.usda.gov/developer/
- https://data.nass.usda.gov/Quick_Stats/

## 20.6 USDA AMS MyMarketNews

Use for agricultural market reports.

Official:
- https://mymarketnews.ams.usda.gov/mymarketnews-api

Requires configured API credentials where applicable.

## 20.7 GBIF

Use for:
- taxonomy support,
- biodiversity occurrence,
- distribution evidence.

Official:
- https://techdocs.gbif.org/en/openapi/

Most read queries do not require authentication.
Respect GBIF citation/data-use rules.

## 20.8 Genesys PGR

Use for global plant genetic resource/germplasm discovery.

Official:
- https://www.genesys-pgr.org/documentation/apis

Do not imply that a listed accession is automatically legally available for shipment or planting.

Sentinel must separately evaluate movement/import restrictions.

## 20.9 Pl@ntNet

Use as one possible visual plant-identification tool.

Current free plan:
- 500 identifications/day.

Official:
- https://my.plantnet.org/pricing
- https://my.plantnet.org/terms_of_use

Required:
- quota adapter,
- attribution compliance,
- no automatic paid upgrade,
- local/multimodal model fallback.

## 20.10 Europe PMC

Use for research discovery and metadata.

Official:
- https://europepmc.org/RestfulWebService

It includes literature from multiple sources and exposes REST access.

Only store/use full text according to applicable rights.

## 20.11 APHIS

Use for current U.S. federal plant-pest/quarantine context.

Official examples:
- https://www.aphis.usda.gov/plant-pests-diseases/fruit-flies/fruit-fly-quarantine-maps-descriptions
- https://www.aphis.usda.gov/plant-imports/regulated-pest-list
- https://www.aphis.usda.gov/organism-soil-imports

Sentinel must not assume all restrictions align exactly to county lines.

## 20.12 State Agriculture Sources

Build jurisdiction packs.

Initial priority:
1. U.S. federal,
2. Texas,
3. Florida,
4. Singapore,
5. additional regions based on users/institutional partners.

Do not scrape a source if an API/download/official dataset is available.

---

# 21. Jurisdiction Pack Interface

A jurisdiction pack is a versioned adapter bundle.

```py
class JurisdictionPack(Protocol):
    id: str
    country_code: str

    async def resolve_zones(self, location, at_time): ...
    async def movement_rules(self, movement_request): ...
    async def pest_alerts(self, location, at_time): ...
    async def agriculture_sources(self): ...
```

Examples:

```text
us_federal
us_tx
us_fl
sg
```

A movement check may combine multiple packs.

Example:
Texas county A -> Florida county B

Relevant:
- origin state rules,
- destination state rules,
- federal interstate rules,
- applicable quarantine polygons,
- regulated article.

Never reduce this to `origin_county != destination_county`.

---

# 22. Economic/Supply-Chain Context

Mercator must differentiate:

1. **live/current market reports**,
2. **periodic production statistics**,
3. **structural supply-chain datasets**,
4. **local economic context**.

Do not describe old structural freight data as live logistics.

Economic recommendations should have:
- observation date,
- geographic scope,
- commodity normalization,
- source.

MVP economic output is contextual.
Do not provide investment advice.

---

# 23. Season Planner Logic

Input:

```text
location
crop/cultivar
goal
planting method
available space
soil/container
water availability
target dates
user constraints
```

Context:
- climate normals,
- weather forecast when near enough,
- crop temperature requirements,
- hardiness/frost context,
- photoperiod,
- growing degree days,
- disease/pest seasonality where available,
- soil,
- drought/water,
- regulations,
- optional market context,
- optional Luna experimental context.

Output:
- planting window,
- confidence,
- task schedule,
- contingencies,
- measurements,
- calendar-ready actions.

Season plans must be versioned.

If weather materially changes, generate a proposed plan revision.
Do not rewrite history.

---

# 24. Vision Requirements

Vision is mandatory in the architecture and should be exposed in the MVP as image upload/camera capture.

MVP image workflows:
- identify plant candidate,
- identify plant part,
- assess visible symptoms,
- estimate image quality,
- ask for better angle/underside/whole-plant image,
- produce differential hypotheses,
- connect with environmental context.

Required confidence behavior:

```text
if image_quality_low:
    do not produce definitive diagnosis

if top_species_candidates_are_close:
    request discriminating image/feature

if disease_hypothesis_high_risk:
    retrieve evidence/source before action

if pesticide_or_regulated_action:
    do not give unrestricted prescriptive instruction
```

Images must be scoped to organization/workspace.

Institution deployments must be able to disable cloud vision providers.

---

# 25. Conversation and Memory

GAIA should have:

- conversations,
- messages,
- attachments,
- selected workspace,
- selected plants,
- temporary context,
- durable plant/farm memory.

Do not treat the entire conversation transcript as permanent memory.

Memory classes:
- user preference,
- farm fact,
- plant fact,
- verified observation,
- inferred hypothesis,
- task,
- outcome.

Inferences must not silently become facts.

---

# 26. Original User Interface

The interaction can be familiar to ChatGPT-style users, but do not make a pixel-for-pixel clone or copy brand assets.

MVP surfaces:

## Home/Chat
- conversation list,
- central chat stream,
- multimodal composer,
- location/context indicator,
- source chips,
- confidence/evidence display.

## Plant Workspace
- plant profile,
- photos,
- observations,
- timeline,
- care plan,
- diagnoses/hypotheses,
- environmental history.

## Season Planner
- crops,
- timeline,
- task plan,
- weather sensitivity,
- calendar sync.

## Sources/Evidence
- sources used,
- retrieval time,
- evidence grade,
- conflicting evidence.

## Location/Atlas
- location,
- county/district,
- jurisdiction,
- applicable regulatory zones,
- privacy precision.

## Institution Workspace
Later:
- members,
- datasets,
- research projects,
- exports,
- organization knowledge.

### Response design

A strong GAIA response should visually separate:

- Answer / Recommendation
- Why
- Actions
- Timing
- Confidence
- Sources
- Regulatory warning where applicable

---

# 27. API Surface

Version API from first release.

Example:

```text
POST /api/v1/chat
POST /api/v1/chat/{conversation_id}/messages
GET  /api/v1/conversations

POST /api/v1/media
POST /api/v1/vision/analyze

GET  /api/v1/plants
POST /api/v1/plants
GET  /api/v1/plants/{id}
POST /api/v1/plants/{id}/observations

POST /api/v1/context/environment
POST /api/v1/context/geography

POST /api/v1/guidance
GET  /api/v1/guidance/{id}

POST /api/v1/movement/check

POST /api/v1/season/plan
POST /api/v1/season/{id}/revise

GET  /api/v1/evidence/{id}
GET  /api/v1/provenance/{id}

GET  /api/v1/cost/status

POST /api/v1/calendar/connect
POST /api/v1/calendar/events/preview
POST /api/v1/calendar/events/commit
```

Use server-sent events or an equivalent simple streaming mechanism for chat responses before introducing WebSockets unnecessarily.

---

# 28. Authentication and Authorization

Do not invent a custom password system if a trusted, zero/low-cost auth option is available.

However, authentication provider must be abstracted.

Authorization is GAIA-owned.

Every protected query includes:
- user,
- organization,
- workspace,
- role,
- permissions.

Data isolation tests are mandatory.

Institution/government deployments must support external identity providers later.

---

# 29. Security Baseline

Required from first meaningful alpha:

- secrets only through environment/secret storage,
- no secrets committed,
- encryption in transit,
- tenant checks on every protected object,
- attachment type/size validation,
- safe filename handling,
- rate limiting,
- CSRF strategy where applicable,
- OAuth state validation,
- secure token storage,
- log redaction,
- source fetch protections against SSRF,
- URL allowlist/validation for adapters,
- SQL parameterization,
- migrations in version control,
- dependency scanning,
- audit events for privileged actions.

Never send an institution’s private dataset to a remote model unless its deployment policy explicitly permits that provider.

---

# 30. Research and University Requirements

GAIA should eventually be credible in university environments by supporting reproducibility rather than merely sounding academic.

Required architecture:

- project/workspace isolation,
- source citation,
- model version tracking,
- prompt/harness version tracking,
- data snapshot metadata,
- exportable provenance,
- dataset imports,
- configurable knowledge collections,
- reproducible query bundles,
- result comparison across model/harness versions,
- researcher annotations,
- outcome data export.

Do not claim that GAIA output is peer reviewed.

A university can use GAIA to retrieve, synthesize, plan, analyze and document; the institution remains responsible for its research governance.

---

# 31. Government / Sovereign Requirements

Architect now for:

- deployment without public SaaS dependency,
- local model,
- local database,
- local object storage,
- customer-controlled encryption keys later,
- external identity integration later,
- configurable logging,
- network egress policy,
- audit export,
- jurisdiction-specific data adapters,
- private knowledge.

Do not implement certification work in MVP.

Use NIST AI RMF principles as design guidance where practical, but do not state that following this document constitutes certification.

---

# 32. Evidence and Safety Policy

Agricultural guidance varies in consequence.

Classify requests by risk.

## Low risk
Examples:
- plant ID,
- planting suggestions,
- watering reminders.

## Moderate risk
Examples:
- disease diagnosis,
- nutrient deficiency,
- soil amendment,
- irrigation volume.

## High risk
Examples:
- pesticide use,
- regulated pest movement,
- quarantine compliance,
- commercial-scale chemical recommendations,
- actions affecting public ecosystems,
- actuator control.

Higher-risk workflows require:
- stronger sources,
- explicit uncertainty,
- location/jurisdiction,
- human confirmation,
- current data where applicable.

---

# 33. Pesticide and Chemical Guidance Boundary

Do not build GAIA v0 as a pesticide application calculator.

When chemical control arises:
- identify nonchemical/IPM options first where appropriate,
- retrieve authoritative label/regulatory guidance,
- communicate that the product label and local law control,
- avoid inventing dose/rate information,
- never bypass label restrictions.

This domain should receive a dedicated future specification.

---

# 34. Caching

Every adapter must define:
- cache key,
- TTL,
- stale-if-error behavior,
- source timestamp,
- source version if available.

Suggested categories:

```text
STATIC/LONG
taxonomy
soil survey
hardiness
plant guides

MEDIUM
regulatory base lists
market reference metadata
research metadata

SHORT
forecast
alerts
current water
market reports

LOCAL COMPUTE
sunrise/sunset
moon phase
unit conversion
growing degree calculations
```

Cache raw provider responses when licensing allows.

---

# 35. Offline and Failure Behavior

GAIA must fail gracefully.

Examples:

Weather unavailable:
- use recent cached result if still defensible,
- clearly mark stale.

PlantNet quota exhausted:
- use local/other configured vision,
- or explain identification capacity is unavailable.

Research API down:
- answer using already indexed approved sources,
- mark inability to refresh evidence.

Regulatory source unavailable:
- do not claim “allowed.”
- return `unresolved` when current verification is required.

Model unavailable:
- deterministic tools should still function.

The app should remain useful even if model inference is temporarily unavailable.

---

# 36. Observability

Local development:
- structured logs,
- request IDs,
- trace IDs,
- tool timing,
- model timing,
- cache hit/miss,
- cost.

Do not pay for an observability vendor in v0.

Required dashboards may be simple internal pages or log queries.

Metrics:
- requests,
- model invocations,
- model-free responses,
- tool errors,
- cache hit rate,
- average latency,
- vision requests,
- free quota remaining,
- cost USD,
- hallucination/eval failures,
- user plan completion.

---

# 37. Evaluation Framework

This is mandatory.

GAIA cannot be judged by “it sounds smart.”

Create a version-controlled evaluation suite.

Initial categories:

## Geography
- coordinate -> correct county/state,
- boundary-edge cases,
- privacy precision.

## Weather
- source freshness,
- units,
- location matching.

## Soil
- correct interpretation of SSURGO as survey context,
- no false live moisture claim.

## Plant ID
- common plant images,
- ambiguous images,
- poor-quality images,
- confidence behavior.

## Diagnosis
- disease vs nutrient vs water-stress differential,
- requires additional observation when ambiguous.

## Regulation
- quarantine polygon cases,
- county line does not automatically imply restriction,
- current source requirement.

## Season
- northern vs southern hemisphere,
- long-range planning vs forecast,
- freeze-sensitive crop.

## Economics
- timestamp attached,
- correct geography,
- no live claim for historical dataset.

## Evidence
- source present,
- evidence grade reasonable,
- contradiction represented.

## Cost
- paid providers disabled,
- quota exhaustion produces graceful fallback,
- no path can spend money automatically.

## Multi-tenancy
- cross-tenant reads impossible,
- attachment isolation,
- calendar credentials isolated.

## Reproducibility
- same stored input bundle can reconstruct data/evidence basis.

### Golden test form

Each eval case should define:
- prompt,
- workspace/location,
- plant/context,
- allowed sources,
- prohibited claims,
- required elements,
- severity.

---

# 38. Initial Evaluation Questions

At minimum GAIA v0 must handle:

1. “What can I grow here this month?”
2. “Will tonight’s weather hurt my tomatoes?”
3. “What is this plant?” with image.
4. “What might be causing these leaf spots?” with image.
5. “What should I do with this tomato today?”
6. “Create a seasonal plan for collards, tomatoes and peppers.”
7. “Show me why you recommend that.”
8. “What does current research say about this hypothesis?”
9. “Find germplasm relevant to heat tolerance.”
10. “Can I move this live citrus plant from origin X to destination Y?”
11. “What county am I in?”
12. “What is the soil context at this location?”
13. “What does the regional market data say about this crop?”
14. “Put these approved season tasks on my Google Calendar.”
15. “What happens if the AI quota is exhausted?”

---

# 39. Development Phases

## Phase 0 — Repository & Constitution

Deliver:
- repository,
- this document,
- comprehension report,
- decisions log,
- environment checks,
- Docker bootstrap,
- lint/test automation,
- basic CI if free.

Acceptance:
- local stack starts,
- no paid dependency required.

## Phase 1 — Identity, Tenancy, Core Domain

Deliver:
- organizations,
- users,
- memberships,
- workspaces,
- locations,
- plants,
- observations,
- conversations,
- migrations,
- access tests.

Acceptance:
- two organizations cannot access each other’s data.

## Phase 2 — Tool Gateway + Cost Firewall

Deliver:
- provider registry,
- cost policies,
- quotas,
- cache abstraction,
- structured provenance envelope.

Acceptance:
- test proves a paid provider cannot execute when disabled.

## Phase 3 — Atlas + Terra

Deliver:
- geospatial context,
- U.S. location normalization,
- NWS,
- NASA POWER,
- USDA soil,
- initial water adapter,
- environmental snapshot.

Acceptance:
- one coordinate can generate a source-backed context bundle.

## Phase 4 — Core Chat + Model Gateway

Deliver:
- model abstraction,
- local model provider,
- streaming,
- tool routing,
- structured `GuidancePlan`.

Acceptance:
- deterministic weather lookup does not require a large-model call.

## Phase 5 — Botanist + Plant Workspace

Deliver:
- canonical plant model,
- GBIF adapter,
- Genesys discovery,
- plant timeline,
- plant profile UI.

Acceptance:
- GAIA can connect a user plant to taxonomy and germplasm context with provenance.

## Phase 6 — Vision

Deliver:
- image upload/camera,
- local/multimodal provider,
- optional Pl@ntNet adapter,
- quality and ambiguity behavior,
- diagnosis workflow.

Acceptance:
- poor image causes request for better evidence rather than fake certainty.

## Phase 7 — Scholar

Deliver:
- Europe PMC adapter,
- retrieval/indexing policy,
- evidence grading,
- source display,
- contradictory evidence.

Acceptance:
- research answer includes verifiable provenance.

## Phase 8 — Sentinel

Deliver:
- U.S. federal pack,
- Texas pack,
- movement request schema,
- regulatory source freshness,
- `allowed|conditional|restricted|unresolved`.

Acceptance:
- GAIA will not infer a legal movement status solely from county difference.

## Phase 9 — Season + Calendar

Deliver:
- planning engine,
- action/task objects,
- Google OAuth,
- preview then commit,
- calendar event binding.

Acceptance:
- GAIA produces plan first;
- user approval is required before calendar writes.

## Phase 10 — Mercator

Deliver:
- NASS,
- AMS,
- first economic context panel,
- timestamped market data.

Acceptance:
- current/historical nature of every economic source is explicit.

## Phase 11 — Institutional Foundation

Deliver:
- researcher role,
- provenance export,
- dataset collections,
- project/workspace exports,
- deployment documentation.

Acceptance:
- a research interaction can be exported with model/source/version metadata.

## Phase 12 — Additional Jurisdiction Packs

Priority proposal:
- Florida,
- Singapore.

Acceptance:
- jurisdiction pack can be installed/disabled without modifying the orchestrator.

---

# 40. MVP Cut Line

The first genuinely useful public/internal MVP should include:

MUST:
- account/workspace,
- location,
- plant records,
- chat,
- image upload,
- model gateway,
- tool gateway,
- Cost Firewall,
- Terra core,
- Atlas core,
- evidence/provenance,
- simple Guidance Plans,
- source display.

SHOULD NEXT:
- Scholar,
- Season,
- Calendar,
- Sentinel Texas/U.S.,
- Mercator.

LATER:
- audio,
- video,
- sovereign installer polish,
- full university dataset workflows,
- BioCube actuators,
- extensive global regulations,
- dedicated graph DB,
- model fine-tuning.

The message and media schema should support future modalities now even if UI exposure is later.

---

# 41. UI Acceptance Criteria

The first UI should feel premium even if infrastructure is free.

Required:
- fast initial load,
- mobile usable,
- camera upload,
- streaming response,
- clear empty states,
- persistent conversations,
- visible selected location,
- visible selected plant/workspace,
- expandable sources,
- confidence labels,
- plan/action cards,
- no technical provider jargon unless user expands details.

Do not expose internal subagent names as clutter unless useful.
Users interact with GAIA; specialists are internal intelligence.

---

# 42. Performance Principles

Targets are provisional and must be measured.

- deterministic tool response: as fast as provider allows,
- cached context: subsecond target,
- first streamed model token: reasonable for hardware,
- image upload: progressive feedback,
- avoid N+1 provider calls,
- parallelize independent read tools,
- cache expensive source normalization,
- do not call the same external API repeatedly within one plan.

---

# 43. Data Privacy

Location and plant data may be sensitive for farms or institutions.

Requirements:
- user controls location precision where possible,
- private institutional locations not made public,
- do not expose exact farm coordinates in shared outputs by default,
- organization policies control model egress later,
- deletion workflow designed from first release,
- attachments and exported datasets have ownership metadata.

---

# 44. Internationalization

Architect from first release for:
- metric and U.S. customary units,
- locale-aware dates,
- timezones,
- southern hemisphere seasons,
- multilingual common names,
- country-specific regulation packs.

Never hard-code:
“summer = June–August”
as a universal rule.

Scientific names are preferred canonical plant identifiers.

---

# 45. Licensing Registry

For every source, record:

```text
source_id
terms_url
license
commercial_use
redistribution
caching
derivative_use
model_training
attribution
last_reviewed_at
review_notes
```

Unknown rights = `unknown`, not `allowed`.

Do not use a source for model training unless training rights are explicitly reviewed.

---

# 46. Model Training and Fine-Tuning Policy

Do NOT fine-tune first.

First build:
- harness,
- tools,
- evaluations,
- outcome data,
- high-quality labeled examples.

Future fine-tuning may improve:
- routing,
- tool selection,
- agricultural response style,
- structured output,
- domain terminology,
- multimodal diagnosis support.

Facts, weather, regulations, prices, and dynamic science do not belong solely in model weights.

Any training dataset must have:
- provenance,
- rights,
- quality review,
- privacy review,
- intended use.

---

# 47. Outcome Graph

The strongest future proprietary asset is the relationship:

```text
context
+ plant/cultivar
+ environment
+ recommendation
+ user action
+ timing
+ outcome
```

GAIA should record this with explicit user/organization permissions.

Outcome data must not be silently pooled across institutions.

Future learning can operate:
- within a user,
- within an organization,
- across consenting populations,
- through privacy-preserving aggregates.

---

# 48. Agent/Framework Policy

LangGraph, Deep Agents, or another agent framework may be used.

They MUST remain implementation adapters, not the business domain.

Do not allow:
- framework-specific message types in core domain entities,
- framework checkpoint schema to become GAIA’s memory model,
- agent framework to own security permissions,
- framework to own Cost Firewall.

GAIA owns orchestration semantics.

---

# 49. Deterministic Calculation Library

Implement local functions for:
- unit conversion,
- growing degree days,
- photoperiod where possible,
- sunrise/sunset,
- lunar phase,
- date windows,
- frost threshold comparisons,
- simple irrigation math where scientifically defensible.

Do not spend model inference on arithmetic.

Each formula must include:
- citation/source where relevant,
- unit tests,
- assumptions.

---

# 50. Data Normalization

GAIA must normalize units internally.

Recommended:
- SI canonical storage where practical,
- preserve original source unit,
- convert for user display.

Every measurement:
```text
value
canonical_unit
original_value
original_unit
source
```

Avoid hidden conversions.

---

# 51. Prompt/Harness Versioning

Prompts are production code.

Store:
- prompt ID,
- semantic version,
- hash,
- intended task,
- model compatibility,
- evaluation score.

Do not make untracked prompt changes in production.

The system prompt should instruct the model to:
- use tool evidence,
- separate observation from inference,
- report uncertainty,
- not invent citations,
- respect location/jurisdiction,
- output structured plans,
- obey tool permissions.

---

# 52. Required Internal Decision Records

Create ADRs for at least:

- ADR-001 modular monolith,
- ADR-002 model gateway,
- ADR-003 PostgreSQL/SQLite strategy,
- ADR-004 provenance model,
- ADR-005 Cost Firewall,
- ADR-006 jurisdiction packs,
- ADR-007 research retrieval,
- ADR-008 calendar write permissions,
- ADR-009 multimodal storage,
- ADR-010 institutional data egress.

---

# 53. Environment Variables

`.env.example` should contain names only, never secrets.

Example:

```text
GAIA_ENV=development
GAIA_TOTAL_INITIAL_BUDGET_USD=20
GAIA_ALLOW_PAID_MODELS=false
GAIA_ALLOW_PAID_APIS=false

DATABASE_URL=
OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_BUCKET=

MODEL_PROVIDER=local
MODEL_BASE_URL=
MODEL_NAME=

NWS_USER_AGENT=
NASA_POWER_BASE_URL=
USDA_NASS_API_KEY=
USDA_AMS_API_KEY=
PLANTNET_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

Do not make all keys required to boot.
GAIA must start with optional adapters disabled.

---

# 54. Local Development Command

Goal:

```bash
cp .env.example .env
docker compose up
```

Then:
- web app available,
- API available,
- database available,
- local model may be separately configured.

Provide:
- `make dev`
- `make test`
- `make lint`
- `make eval`
- `make seed`

or platform-neutral equivalents.

---

# 55. CI

Use free CI if available.

Minimum:
- lint,
- unit tests,
- migrations,
- cost tests,
- tenant isolation tests,
- adapter contract tests with mocked providers,
- small eval suite.

Do not run expensive model evals automatically on every commit under the $20 constraint.

Use fixture/replay data for most CI.

---

# 56. Adapter Contract Testing

External APIs change.

Each adapter should have:
- parser unit tests,
- sample response fixtures,
- timeout,
- retry policy,
- circuit breaker behavior,
- schema validation,
- cache behavior,
- source provenance.

Live smoke tests can run manually or on a low frequency.

---

# 57. Provider Change Resilience

Known example:
USGS legacy WaterServices is expected to be decommissioned in early 2027.

Therefore:
- never expose provider response shapes directly to UI,
- normalize all provider data,
- provider migrations should not change domain objects.

This principle applies to every API.

---

# 58. Institutional Knowledge

Future institution workspaces need private retrieval.

Design:

```text
KnowledgeCollection
- id
- organization_id
- workspace_id optional
- visibility
- name
- documents[]
- embedding_provider
- source policy
```

A government collection can be configured:
- local embeddings only,
- local model only,
- no egress.

Do not implement complex institutional RAG before core provenance is stable.

---

# 59. Document Ingestion

Future supported:
- PDF,
- CSV,
- DOCX,
- images,
- text,
- research exports.

Ingestion pipeline:
- virus/file validation where appropriate,
- metadata,
- text extraction,
- chunking,
- rights flag,
- embeddings,
- source-level permissions.

Never assume uploaded content may be used to train global GAIA.

---

# 60. Regulatory Freshness Rules

Regulatory data must carry freshness.

Possible policy:
- current quarantine: short TTL,
- state regulation page: configurable TTL,
- static statute reference: longer TTL,
- cached fallback only if clearly dated.

Movement check response should show:
- checked at,
- authority,
- applicable rule,
- unresolved questions.

If live verification is unavailable and it matters, return unresolved rather than allowed.

---

# 61. Evidence Response Contract

Example:

```json
{
  "claim": "Delay transplanting because of cold-stress risk.",
  "confidence": 0.91,
  "evidence_grade": "B",
  "support": [
    {
      "source_id": "nws-...",
      "fact": "forecast overnight low ..."
    },
    {
      "source_id": "crop-profile-...",
      "fact": "crop threshold ..."
    }
  ],
  "contradictions": []
}
```

The LLM may phrase the recommendation.
It may not fabricate the evidence objects.

---

# 62. Vision Research-Grade Behavior

For universities, retain optional structured image metadata:
- capture time,
- location if authorized,
- plant ID,
- growth stage,
- camera/device metadata if permitted,
- lighting quality,
- image quality score,
- model version,
- predictions,
- user/researcher verification.

This allows later evaluation of model performance.

Do not use private institutional images for global model improvement without agreement.

---

# 63. Accessibility

Minimum:
- semantic HTML,
- keyboard support,
- screen-reader labels,
- sufficient contrast,
- image alt/description workflow,
- focus states,
- status announcements for streaming/loading.

Agricultural users may be outdoors on phones.
Large touch targets matter.

---

# 64. Maps

Atlas should expose map-ready geometry but maps are not required to block MVP.

When implemented:
- display approximate user location depending on privacy setting,
- quarantine/regulatory overlays,
- county/district,
- watershed,
- optional soil layers.

Do not imply a polygon boundary is legally definitive if the authority describes it as guidance only.

---

# 65. Community Knowledge

Community knowledge belongs in a separate evidence class.

Store:
- author/context,
- region,
- crop,
- date,
- observation,
- outcome where available.

Do not merge community experience into scientific evidence without labeling.

This is important to GAIA’s identity: human experience remains visible rather than being flattened into an LLM answer.

---

# 66. GreensWrld Integration

Not MVP-blocking, but design GAIA APIs so GreensWrld can later:
- create/update plant records,
- send observations,
- request Guidance Plans,
- display source/evidence,
- complete actions,
- send outcomes.

GAIA is the intelligence service.
GreensWrld is one client/experience surface.

Do not couple GAIA core to GreensWrld UI code.

---

# 67. BioCube Integration

Future BioCube integration should be event/sensor based.

Design provider interface now, implementation later.

BioCube may provide:
- sensor observations,
- resource use,
- environment,
- crop outcomes.

Actuation requires:
- device authentication,
- command authorization,
- safety constraints,
- audit trail,
- failsafe behavior,
- human approval policies.

Never let a general chat prompt directly operate physical infrastructure.

---

# 68. Public API Future

GAIA should eventually expose an institution/API product.

Prepare:
- stable versioned domain objects,
- scoped API tokens later,
- rate limits,
- organization billing later,
- source attribution.

Do not build monetization before usage proves the need.

---

# 69. Subscription Economics — Deferred

The future consumer subscription price is intentionally irrelevant to Protocol Two.

Do NOT use future subscription revenue to justify current waste.

Architecture must be efficient before revenue.

Future pricing belongs in a separate business/economics plan.

---

# 70. Definition of “Done” for Protocol Two Implementation

The first build is not done when a chatbot responds.

It is done when:

- local environment boots reproducibly,
- multi-tenancy is enforced,
- model gateway works,
- paid model usage is impossible by default,
- a location creates a GeoContext,
- environmental tools create a provenance-backed snapshot,
- an image can enter the Vision workflow,
- a user can register a plant and observation,
- GAIA can produce a structured GuidancePlan,
- sources are shown,
- uncertainty is represented,
- one quota-exhaustion test passes,
- one cross-tenant access test fails safely,
- basic evals run,
- documentation explains how to add a new provider and jurisdiction pack.

---

# 71. Known Questions Codex Must Surface Before Irreversible Choices

Codex must verify these with the project owner if not already known from the repository/environment:

1. What hardware is available locally? CPU, RAM, GPU model, VRAM, OS.
2. Is this a new repository or an existing Cillian/GreensWrld repository?
3. What domain/subdomain will be used for the first alpha?
4. Is the first alpha private, invite-only, or public?
5. Which authentication provider, if any, is already used by Cillian Industries?
6. Is Texas the initial live jurisdiction pack?
7. Should Florida be the second U.S. jurisdiction pack because of FAMU goals?
8. Should Singapore be the first non-U.S. jurisdiction pack?
9. Which existing Cillian brand tokens/components may GAIA reuse?
10. What exact hardware must local multimodal inference support?
11. Is Google Calendar required in the first public alpha or immediately after?
12. What user data from GreensWrld is legally/technically available to import?
13. Are there existing plant/outcome schemas that GAIA must preserve?
14. What telemetry may Cillian collect from institutional deployments?
15. What deletion/retention expectation should personal users receive?
16. Are minors/students expected to use university deployments?
17. Should voice/audio be exposed in v0 or only supported by the backend schema?
18. What languages are first priority after English?
19. What is the initial geographic privacy default: exact, 100m, 1km, county?
20. Who may approve enabling any paid provider in the future?

Codex should ask only unresolved questions, not repeat answered decisions.

---

# 72. Initial Answers to Assume Unless Owner Overrides

To prevent unnecessary blocking, use these defaults:

- Architecture: modular monolith.
- Geography: U.S.-first, global-ready.
- First jurisdiction implementation: U.S. federal + Texas.
- Next jurisdiction targets: Florida, then Singapore.
- Language: English first.
- Units: user-configurable; store canonical units.
- Vision: image input is MVP; audio/video architecture only at first.
- Calendar: design now; implement after core Season functionality unless owner prioritizes it earlier.
- Model: provider-neutral; benchmark Nemotron 3 Nano Omni, do not hard-depend on it.
- Hosting: local-first; free hosted tier only after local works.
- Paid APIs: disabled.
- Cash spend: $0 target.
- Data store: PostgreSQL preferred.
- Vector: pgvector only if needed.
- Graph DB: no.
- Microservices: no.
- Compliance claims: no.
- Fine-tuning: no, until evaluations/outcome data justify it.
- Regulations: current authoritative retrieval required for high-risk movement decisions.
- Luna: experimental context only.
- Community knowledge: preserved and labeled separately.
- Calendar writes: preview/confirmation before commit.
- BioCube physical control: deferred.

---

# 73. First Codex Implementation Sequence

After interrogation/decisions:

### Commit 1
Repository constitution, README, ADRs, dev scripts, Docker, lint/test.

### Commit 2
Domain models + database + tenancy.

### Commit 3
Provider registry, Cost Firewall, provenance envelope, cache abstraction.

### Commit 4
Atlas foundation + location resolution interfaces.

### Commit 5
Terra: NWS + NASA POWER + soil adapter.

### Commit 6
Model Gateway + local provider + structured output.

### Commit 7
Conversation + GuidancePlan API.

### Commit 8
Web UI chat + sources + location.

### Commit 9
Plant workspace.

### Commit 10
Vision image pipeline.

Then run evaluations before expanding.

Do not implement ten agents simultaneously.

---

# 74. Source Verification Snapshot — 2026-08-10

The following assumptions were specifically rechecked during Protocol Two preparation:

- **Nemotron 3 Nano Omni:** NVIDIA describes it as a unified 30B-A3B model for text, image, audio, and video.
  - https://developer.nvidia.com/blog/nvidia-nemotron-3-nano-omni-powers-multimodal-agent-reasoning-in-a-single-efficient-open-model

- **Cloudflare Workers AI:** current documentation lists 10,000 free Neurons/day, with Workers Free requiring upgrade to exceed that allocation.
  - https://developers.cloudflare.com/workers-ai/platform/pricing/

- **Google Calendar:** events can be created through `events.insert()` with OAuth authorization.
  - https://developers.google.com/workspace/calendar/api/guides/create-events

- **USDA Soil Data Access:** provides real-time web-service access to official soil survey spatial/tabular data.
  - https://sdmdataaccess.nrcs.usda.gov/

- **NASA POWER:** exposes REST APIs, including hourly solar/meteorological data from 2001 to near-real-time.
  - https://power.larc.nasa.gov/docs/services/api/temporal/hourly/

- **USGS Water:** legacy WaterServices is scheduled for decommissioning in early 2027; build through a provider interface and plan migration to `api.waterdata.usgs.gov`.
  - https://waterservices.usgs.gov/

- **NASS:** official agricultural statistics and Census of Agriculture data are available through NASS developer tools/Quick Stats.
  - https://www.nass.usda.gov/developer/

- **USDA AMS MyMarketNews:** exposes an API for Market News report data.
  - https://mymarketnews.ams.usda.gov/mymarketnews-api

- **GBIF:** provides a stable REST API for biodiversity/taxonomic/occurrence access.
  - https://techdocs.gbif.org/en/openapi/

- **Genesys PGR:** provides API documentation for plant genetic resource data.
  - https://www.genesys-pgr.org/documentation/apis

- **Pl@ntNet:** current free tier lists 500 identifications/day.
  - https://my.plantnet.org/pricing

- **Europe PMC:** provides REST access to life-science literature and metadata.
  - https://europepmc.org/RestfulWebService

- **APHIS:** current quarantine/regulated-area information may change and is maintained through current web resources; this must be retrieved/cached as current regulation data rather than memorized.
  - https://www.aphis.usda.gov/plant-pests-diseases/aphis-streamlines-domestic-quarantines-certain-plant-pests

Codex must re-verify external service terms, quotas, and APIs whenever an adapter is actually implemented.

---

# 75. Final Directive to Codex

Build GAIA as though the first user is a grower with one tomato plant **and** the thousandth deployment is a university or government that asks:

- Where did this recommendation come from?
- What data left our infrastructure?
- Which model produced it?
- Which regulation was current at the time?
- What did this cost?
- Can we reproduce it?
- Can we replace the model?
- Can we run it ourselves?

The architecture must have defensible answers.

At the same time, do not over-engineer the first version.

The first version should run locally, cost essentially nothing, accept an image, know where the user is, retrieve real agricultural context, distinguish facts from hypotheses, and turn that evidence into an actionable Guidance Plan.

**Build the harness first.  
Build the evidence system first.  
Build the cost controls first.  
Make the model replaceable.  
Let outcome data become the moat.**

---

# END — PROTOCOL TWO
