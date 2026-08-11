# CHANGELOG

## Unreleased

- Added Phase 8 Sentinel regulatory provider boundary, APHIS/Texas fixture adapters, read-only regulatory smoke adapter, Tool Gateway wrappers, SentinelService, deterministic rule matching, movement decision persistence, and minimal Sentinel UI diagnostics.
- Added migration `0008_sentinel_regulatory_intelligence.sql` for strengthened regulatory rule fields, movement requests, movement decisions, and Sentinel zone features.
- Added Phase 8 tests covering citrus movement, federal/state rule aggregation, unknown data fail-closed behavior, conflicts, freshness, tenant/privacy boundaries, Cost Firewall behavior, caching, Vision/Genesys escalation, plant-part distinctions, exceptions, and optional APHIS/Texas live smoke.
- Added Phase 7 Scholar research provider boundary, Europe PMC live-capable adapter, fixture research provider, research Tool Gateway wrappers, ScholarService, citation validation, deterministic query planning, evidence synthesis prompt harness, and research API helpers.
- Added migration `0007_scholar_research_evidence.sql` for research works, authors, claims, evidence syntheses, collections, and private annotations.
- Added Phase 7 tests covering normalized retrieval, deduplication, missing DOI identity, fetch provenance, provider outages, contradictions, study types, retractions, applicability mismatch, citation validation, tenancy, retrieved-content injection boundaries, cost/cache behavior, no-result honesty, Botanist/Vision integration, and optional Europe PMC smoke.
- Added Phase 6 Vision provider boundary, fixture vision provider, local Ollama LLaVA adapter, Pl@ntNet adapter boundary, Vision Tool Gateway wrappers, VisionService, visual-analysis API helpers, and development UI diagnostics.
- Added migration `0006_vision_multimodal_perception.sql` for persisted visual analyses linked to tenant, workspace, media, plant, geo, environment, and model-run records.
- Added Phase 6 tests covering provider capabilities, visual observation/hypothesis separation, diagnosis overclaim rejection, tenant/media isolation, Tool Gateway/Cost Firewall use, private-image egress denial, cache behavior, Pl@ntNet optionality, provider failure semantics, and optional local LLaVA smoke.
- Added Phase 5 Botanist, GBIF taxonomy boundary, Genesys PGR germplasm boundary, canonical plant profile generation, expanded UserPlant/Observation fields, plant-aware orchestration context, Plant Workspace API helpers, and plant workspace development UI.
- Added migration `0005_botanist_plant_workspace.sql` for expanded plant/taxonomy/user-plant/observation fields, plant-linked conversations/guidance, and `plant_profiles`.
- Added Phase 5 tests covering accepted/synonym/ambiguous/unresolved taxonomy, tenant boundaries, provenance/conflicts, germplasm caveats, cached botanical facts, plant-aware chat context, model-run accounting, and GBIF/Genesys outage behavior.
- Added Phase 4 Model Gateway, local Ollama adapter, normalized model request/response/capability types, fixture model provider, prompt harness versioning, structured GuidancePlan validation, and ModelRun request/response hashing.
- Added Phase 4 GAIA orchestrator, deterministic chat routing, conversation/message persistence, chat API helpers with simple streaming events, and development chat diagnostics UI.
- Added migration `0004_chat_model_gateway.sql` for prompt harnesses, conversations, messages, and expanded ModelRun audit fields.
- Added Phase 4 tests covering Atlas-only geography chat, Atlas/Terra environment chat, local-model reasoning, malformed model safe failure, citation rejection, prompt-injection boundaries, model permissions, streaming events, and persistent conversations.
- Added Phase 3 Atlas service, coordinate privacy reduction, geospatial provider interfaces, regulatory geometry foundation, Terra service, environmental provider interfaces, fixture adapters, live response normalizers, deterministic calculations, context compiler, and context API boundary.
- Added migration `0003_atlas_terra_context.sql` for expanded `GeoContext`, expanded `EnvironmentalSnapshot`, and future Atlas zone features.
- Added Phase 3 tests covering geography, FIPS, non-U.S. structures, privacy reduction, weather timestamps/units, partial provider failures, SSURGO semantics, provenance, zero model calls, Cost Firewall use, exact-location egress denial, cache stale state, and API output shape.
- Added Atlas/Terra architecture docs and NWS, NASA POWER, USDA Soil Data Access, and USGS Water data-source notes.
- Added Phase 2 provider registry, Cost Firewall enforcement, quota checks, Tool Gateway, execution context, egress policy, cache backend, provenance records, source snapshots, audit events, usage ledger, provider health monitor, mock tools, and cost status service.
- Added migration `0002_tool_cost_provenance.sql` for local usage, audit, cache, and snapshot persistence.
- Added Phase 2 tests covering cost denial, quota exhaustion, cache fallback, permissions, tenant checks, egress denial, provenance, failure handling, audit, and usage reporting.
- Added Phase 1 canonical domain dataclasses for identity, tenancy, locations, plants, observations, guidance, provenance, regulations, season planning, calendar bindings, and model runs.
- Added SQLite migration `0001_core_domain.sql` with UUID text identifiers, timestamps, retention metadata, tenant-scoped foreign keys, indexes, and soft-delete fields.
- Added repository boundary enforcing organization/workspace ownership for normal reads and writes.
- Added automated tests for cross-tenant read/write protection, workspace ownership, plant/observation/media isolation, guidance provenance links, soft deletion, cost defaults, and external-key-free domain construction.
- Initialized GAIA Protocol Two repository scaffold.
- Copied governing `GAIA_MASTER_BUILD_PLAN.md` into the repository.
- Added comprehension report, open questions, and decisions log.
