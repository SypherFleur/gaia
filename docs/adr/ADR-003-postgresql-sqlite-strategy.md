# ADR-003: PostgreSQL and SQLite Strategy

Status: Accepted

## Context

GAIA needs relational integrity, multi-tenancy, migrations, and future vector support while remaining easy to run locally.

## Decision

PostgreSQL is preferred for development when Docker is available. SQLite is allowed as a constrained local fallback. Production targets PostgreSQL-compatible storage. pgvector is optional and only introduced when needed.

## Consequences

- The domain model should avoid provider-specific database assumptions where practical.
- Tests must cover tenant isolation regardless of database backend.
- A separate vector database is deferred.

