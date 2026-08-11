# CHANGELOG

## Unreleased

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
