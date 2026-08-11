# DECISIONS

This file records resolved architectural decisions from Protocol Two and the initial repository/environment inspection.

## D001. Protocol Two Governs GAIA

`GAIA_MASTER_BUILD_PLAN.md` is the build constitution. GAIA implementation must preserve provenance, tenant isolation, model replaceability, multimodality, sovereign deployment capability, and Cost Firewall constraints from the first commit.

## D002. New Repository

No existing GAIA/Cillian/GreensWrld repository was present in the inspected workspace. A new GAIA monorepo was initialized at `C:\Users\Jason\Documents\Codex\2026-08-10\sites-plugin-sites-openai-bundled-create\gaia`.

## D003. Modular Monolith

GAIA v0 will be a modular monolith with explicit package boundaries. Microservices are deferred until a demonstrated scaling, security, isolation, or ownership need exists.

## D004. Primary Product Object

`GuidancePlan` is the primary product object. Chat is a human interface over structured guidance, evidence, actions, timing, uncertainty, risk, and provenance.

## D005. Multi-Tenancy From First Migration

Organizations, memberships, workspaces, locations, plants, observations, attachments, credentials, knowledge collections, and guidance outputs must be tenant-scoped from the beginning. Cross-tenant access tests are mandatory.

## D006. Local-First Deployment

GAIA Local comes first. Docker Compose, local database, local object storage, and local model endpoints are preferred. Hosted/free infrastructure may follow only after local works.

## D007. Financial Constitution

Initial total cash budget is USD 20. Development cash spend target is USD 0. Committed monthly infrastructure target is USD 0. Automatic paid models, APIs, infrastructure upgrades, storage upgrades, and overage billing are disabled.

## D008. Cost Firewall

Every external provider and model/tool invocation must be governed by provider cost policy, quota/rate limits where applicable, `hardMonthlyUsd = 0` by default, `allowOverage = false`, and auditability by provider, user, organization, and feature.

## D009. Paid Fallback Disabled

Quota exhaustion or provider failure must fall back to cached data, deterministic computation, local data, approved free sources, smaller free/local models, local inference, graceful degradation, or an unavailable-capacity message. It must not become a paid request automatically.

## D010. Provider-Neutral Model Gateway

Model access must go through a `ModelProvider` abstraction with capabilities and policy-based selection. GAIA must not hard-code domain objects, prompts, storage, or tool logic to any one model provider or runtime.

## D011. Nemotron Candidate Only

NVIDIA Nemotron 3 Nano Omni is a candidate to benchmark, not a hard dependency. The observed 6 GB VRAM reinforces that smaller local models and adapter flexibility are needed.

## D012. Tool Gateway Required

All external actions pass through Tool Gateway definitions with risk class, required permissions, cost policy, input schema, and output schema. LLMs must not bypass this gateway.

## D013. Evidence and Provenance First

Every external datum must carry source, retrieval, validity, license, attribution, freshness, and confidence metadata. LLMs may phrase recommendations but may not fabricate evidence objects.

## D014. PostgreSQL Preferred, SQLite Fallback

Development should use PostgreSQL through Docker when available. SQLite is an acceptable constrained local fallback. Production should prefer PostgreSQL-compatible storage.

## D015. pgvector Optional

Use pgvector only if vector retrieval is needed with PostgreSQL. Do not introduce a separate vector database in v0.

## D016. No Dedicated Graph Database in v0

Graph relationships should be modeled relationally first. A graph database is deferred until query patterns prove a measurable need.

## D017. Image Vision MVP

Image upload/camera capture is part of MVP. Audio/video should be supported in schema and architecture but not exposed in v0 UI unless later reprioritized.

## D018. Vision Cannot Diagnose Alone

Vision output must be differential and evidence-aware. Poor image quality, ambiguity, high-risk disease hypotheses, pesticide actions, or regulated actions require caution, additional evidence, or authoritative retrieval.

## D019. Specialist Modules Are Logical

Terra, Atlas, Sentinel, Botanist, Scholar, Mercator, Season, Luna, and Vision are logical specialists. They do not require separate services or separate LLM calls.

## D020. U.S.-First, Global-Ready Geography

The first jurisdiction implementation is U.S. federal plus Texas. Florida and Singapore follow by default. Architecture must stay global-ready.

## D021. Jurisdiction Packs

Jurisdiction packs are versioned adapter bundles. Movement checks may combine federal, origin, destination, and quarantine-specific rules. County difference alone must never determine legal status.

## D022. Calendar Write Confirmation

Google Calendar uses OAuth. Calendar creates and meaningful updates require user confirmation. Deletes require explicit user action. Silent rescheduling is deferred unless a future automation policy permits it.

## D023. Auth Provider Abstracted

Do not build a custom password system if a trusted zero/low-cost provider is available. GAIA owns authorization regardless of identity provider.

## D024. Sovereign Egress Control

Institutional and sovereign deployments must support local model/database/object storage and no protected content sent to Cillian or remote model providers unless policy explicitly permits it.

## D025. Community Knowledge Separate

Community knowledge is preserved as a distinct evidence class and must not be flattened into scientific or government evidence.

## D026. Luna Experimental

Lunar context is experimental unless crop-specific evidence is sufficient. It must not override high-confidence agronomic evidence.

## D027. Fine-Tuning Deferred

Do not fine-tune first. Build harnesses, evaluations, outcome data, and labeled examples before considering training.

## D028. Agent Frameworks Are Adapters

LangGraph, Deep Agents, or similar frameworks may be used only as implementation adapters. They must not own GAIA domain entities, memory model, security, permissions, or Cost Firewall.

## D029. Prompt Versioning

Prompts are production code and must be versioned with ID, semantic version, hash, task, model compatibility, and evaluation score.

## D030. Deterministic Calculation Library

Arithmetic and defensible local formulas such as unit conversion, growing degree days, photoperiod, sunrise/sunset, lunar phase, date windows, frost thresholds, and simple irrigation math must not spend model inference.

## D031. Data Normalization

Store canonical units where practical, preserve original units and source, and avoid hidden conversions.

## D032. Licensing Registry

Every source requires license, terms, caching, redistribution, derivative use, training rights, attribution, and review metadata. Unknown rights are `unknown`, not `allowed`.

## D033. No Compliance Claims

Do not claim compliance certifications, peer review, legal guarantee, or pesticide authority until separately achieved.

## D034. Phase Order

Implementation follows Protocol Two: constitution and scaffolding first, then domain/tenancy, provider registry/Cost Firewall/provenance, Atlas, Terra, Model Gateway, GuidancePlan API, UI, plant workspace, vision, then evaluations before expansion.

## D035. GAIA Canonical Domain Is Standalone

GAIA is a standalone canonical intelligence platform. Its core schema will not depend on GreensWrld or any existing Cillian application schema. Future GreensWrld integration must use an adapter/mapping layer: `GreensWrld -> GAIA Integration Adapter -> GAIA Canonical Domain`.

## D036. Future GreensWrld Mapping

If GreensWrld schemas become available later, inspect them and create migrations/import mappings without changing GAIA's core architecture unless there is a compelling documented reason.

## D037. Provider-Neutral Authentication Boundary

GAIA will not bind to a commercial authentication provider in Phase 1. It will define a provider-neutral authentication boundary that can later support institutional SSO/OIDC, Google identity, or another provider without changing domain models.

## D038. Development Identity Provider

Local development may use a safe development identity provider with deterministic local users and organizations for tests. Development authentication is not production authentication. Authorization and tenancy remain GAIA-owned.

## D039. Retention Default for Active Data

Active user and workspace data is retained while the account/workspace exists unless the user or organization deletes it.

## D040. User-Requested Deletion Default

User-requested deletion immediately marks data inaccessible to normal application use. Eligible personal content should be hard-deleted within 30 days, associated media/object-storage content removed, and derived records deleted or anonymized where legally and technically appropriate.

## D041. Retention Metadata in Schema

Retention policy metadata must exist in the schema so personal, research, institution, and audit/security retention policies can evolve without redesigning core objects.

## D042. Minimal Operational Telemetry

GAIA Public may initially collect only minimum necessary operational telemetry: request ID, timestamps, latency, tool/provider used, model identifier/version, error classification, quota/cost information, cache hit/miss, and coarse feature usage.

## D043. Telemetry Exclusions

Raw conversations, private documents, exact farm coordinates, images, and institutional datasets must not enter analytics/telemetry by default.

## D044. Institution and Sovereign Telemetry Control

GAIA Institution and GAIA Sovereign must eventually support full telemetry disablement, local-only operation, and administrator configuration. Private institutional data may not be silently transmitted to Cillian Industries.

## D045. Location Privacy Default

Ordinary consumer/public accounts default to `privacy_precision = "approximate"`. Architecture must also support exact, 100m, 1km, county/district, and custom institutional policy.

## D046. Exact Coordinate Handling

GAIA stores and uses exact coordinates only when a feature requires them and the user has authorized their use. Exact farm/private-property coordinates must not be exposed in shared/public responses by default. Precise coordinates may be used internally for agronomic calculations while external presentation is privacy-reduced.

## D047. Local Model Development Strategy

Do not make Nemotron 3 Nano Omni mandatory for local development. Use the existing lightweight Ollama text model for ordinary development/testing and the existing LLaVA model for initial image/vision plumbing where practical. Automated tests should rely heavily on mocks/fixtures and must not require a running GPU model.

## D048. Nemotron Benchmark Deferred

Nemotron 3 Nano Omni remains a primary future multimodal benchmark candidate. Create a future benchmark task rather than forcing a 30B multimodal model into the detected 6 GB VRAM development machine.

## D049. Docker Not Blocking Phase 1

Docker Desktop being stopped is not an architectural blocker for Phase 1 work that does not require live containers. Before relying on live containers, verify Docker Desktop can be started and `docker compose up` works. Do not modify operating-system services destructively.

## D050. Locked Initial Geography

GAIA is U.S.-first and global-ready. U.S. federal plus Texas are the first jurisdiction implementation, Florida is next, and Singapore is the first planned non-U.S. jurisdiction. The core schema must not assume U.S.-only geography.

## D051. Calendar Domain Now, OAuth Later

Google Calendar remains required but does not block Phase 1. Implement `Action`, `SeasonPlan`, and `CalendarBinding` domain objects now. Actual OAuth/calendar integration occurs in the Season/Calendar phase.

## D052. No Special Minor Workflow in MVP

Do not design a special student/minor workflow yet. Institution architecture must support organization policies and roles, but GAIA Public should not intentionally target children in the MVP.

## D053. English First, Locale-Aware Architecture

English is first. Architecture remains locale-aware and Unicode-safe. Do not spend MVP time implementing multilingual generation.

## D054. Provider Registry Before Live Adapters

GAIA maintains a canonical provider registry before implementing live agricultural adapters. Provider records include identity, type, authority, enabled state, billing class, cost policy, quota policy, authentication requirement, geography, cache policy, license metadata, attribution, health status, and remote/local execution posture.

## D055. No Manual-Paid Provider Enabled by Default

Provider registry records may describe future `MANUAL_PAID` providers, but no manual-paid provider may be enabled by default. Credentials never imply authorization to spend money.

## D056. Tool Calls Must Pass Cost Firewall

Every provider-backed tool/model invocation must pass provider lookup, enabled-state check, cost policy, budget policy, overage policy, and quota policy before execution.

## D057. Quotas Are Independent of Cost

Free/local providers may still have quota limits. Quota exhaustion must deny execution or use approved cache/fallback behavior; it must not trigger paid upgrade or paid fallback.

## D058. Local Usage Ledger

GAIA records local usage events for provider/tool/model calls, including organization, user, workspace, provider, request, usage units, estimated/actual cost, cache hit status, and final status. Free/local calls still record utilization with zero estimated cost.

## D059. Tool Gateway Owns External Execution

LLMs and application code must invoke providers through the GAIA Tool Gateway. The gateway enforces authentication context, tenant authorization, permissions, tool risk policy, provider state, Cost Firewall, quota checks, egress policy, execution, provenance capture, audit, and usage records.

## D060. Tool Execution Context Is Canonical

Each tool invocation receives a `ToolExecutionContext` containing request ID, user, organization, workspace, optional conversation/location, permissions, deployment mode, data egress policy, cost policy, and timestamp. Tools must not reconstruct tenant identity from global state.

## D061. Egress Policy Blocks Protected Remote Use

Data egress policy can independently allow or deny public data, private text, private images, private documents, and exact location egress. Remote providers must be denied before execution when protected data egress is forbidden.

## D062. Provenance Envelope Required for Tool Results

Successful tool results produce or reference provenance records. Unknown source fields remain null or `unknown`; GAIA must not fabricate source metadata.

## D063. Shared Cache Infrastructure

Tools use a provider-neutral cache backend. Cache records track key, provider, freshness, stale window, content hash, provenance reference, and payload. Tools must not invent separate cache systems.

## D064. Source Snapshots by Content Hash

Raw source snapshots may be preserved by content hash when licensing and storage policy allow. Secrets and authorization headers must not be persisted. Public source snapshots may be tenant-independent unless the payload contains user-specific information.

## D065. Local Provider Health State

Provider health starts simple and local: unknown, healthy, degraded, unavailable, quota exhausted, or disabled. Repeated provider failures mark providers degraded/unavailable and prevent endless retry loops.

## D066. Audit Events Exclude Private Raw Payloads

Tool execution audit events record actor, organization, workspace when valid, action, tool/provider, result, reason, timestamp, cost, and provenance reference. Raw private prompts, images, documents, exact coordinates, and secrets are not written into audit metadata.

## D067. Phase 2 Stops Before Live Atlas/Terra

Phase 2 intentionally implements rails and deterministic test tools only. NWS, NASA, USDA, USGS, APHIS, Pl@ntNet, Google Calendar, hosted models, and live agricultural adapters are deferred until Phase 3+.

## D068. Atlas Answers Zone Containment, Not Legal Meaning

Atlas resolves administrative geography, watershed, hardiness, and geometry-zone containment. Sentinel later interprets legal/regulatory meaning for movement or compliance decisions.

## D069. Coordinate Privacy Is Presentation-Level

Privacy-reduced coordinates are generated for display/API output without mutating stored authorized source coordinates. Exact coordinates may be used internally when authorized, but remote egress must be blocked when exact-location egress policy forbids it.

## D070. Terra Compiles Context Without LLMs

Terra builds `EnvironmentalSnapshot` objects through deterministic tools, provider-normalized data, cache, and local calculations. It must not create `ModelRun` records or require model inference for Phase 3 context generation.

## D071. Environmental Evidence Type Is Mandatory

Environmental values must preserve evidence semantics such as `FORECAST`, `MODELED`, `SURVEY`, and `DERIVED`. NASA POWER modeled data and SSURGO survey data must never be represented as direct sensor readings.

## D072. Partial Environmental Snapshots Are Valid

One unavailable Terra provider must not fail the entire `EnvironmentalSnapshot`. Provider statuses are attached so consumers can distinguish available, unavailable, unsupported, rate-limited, and provider-error contexts.

## D073. Phase 3 Provider Calls Stay Fixture-Tested

Phase 3 implements provider boundaries and live normalizer classes for NWS, NASA POWER, and USDA Soil Data Access, but automated tests use fixtures/replay data and do not call live services.

## D074. USGS Water Boundary First

Because USGS WaterServices is scheduled for early-2027 decommissioning, GAIA starts with a normalized water-provider interface and fixture-backed nearby-site context rather than coupling domain objects to the legacy API shape.

## D075. Model Gateway Is Provider-Neutral

GAIA routes inference through `ModelProvider`, `ModelRequest`, `ModelResponse`, and `ModelCapabilities`. Domain and orchestration code must not depend directly on Ollama, llama.cpp, hosted APIs, or any specific model family.

## D076. Local Ollama Is An Adapter, Not A Dependency

Phase 4 supports local Ollama because it is installed and has local models available, but Ollama remains replaceable behind the Model Gateway. `llama3.1:latest` is the Phase 4 local smoke-tested text model.

## D077. Deterministic Routing Precedes Model Selection

The GAIA orchestrator must classify and execute deterministic Atlas/Terra routes before model selection. Geography and environmental context questions must produce zero ModelRuns.

## D078. Model Reasoning Requires Explicit Permission

Reasoning routes require `model.chat`. Deterministic geography/environment routes can execute with tool/context permissions and do not require model permission.

## D079. Prompt Harnesses Are Versioned Production Assets

Prompts are tracked by prompt ID, semantic version, schema, compatibility metadata, and stable prompt hash. Per-request and per-response hashes belong on ModelRun records, not on the prompt harness identity.

## D080. GuidancePlan Persistence Requires Validation

Malformed model output must not reach GuidancePlan persistence. GAIA may persist the ModelRun for audit, but the domain GuidancePlan is created only after structured-output validation succeeds.

## D081. Model Citations Are Rejected

Model-generated source IDs, citation IDs, and citation lists are not trusted. GAIA attaches trusted source records from the already-compiled ContextBundle after validation.

## D082. Retrieved Content Is Untrusted For Instructions

Retrieved environmental/geographic content may be evidence, but it is not allowed to modify system, tool, privacy, citation, or cost policy. Prompt-injection tests must preserve this boundary.

## D083. Chat Memory Is GAIA-Owned

Conversations and messages are persisted in GAIA tables. Agent framework checkpoint formats or provider-specific chat formats must not become GAIA's permanent memory model.
