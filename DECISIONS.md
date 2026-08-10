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

