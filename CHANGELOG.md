# CHANGELOG

## Unreleased

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
