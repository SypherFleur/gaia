# ADR-001: Modular Monolith

Status: Accepted

## Context

Protocol Two requires GAIA v0 to run locally, cost essentially nothing, stay understandable, and preserve explicit package boundaries for future extraction.

## Decision

GAIA v0 will be implemented as a modular monolith. Internal modules will expose clear interfaces for orchestration, domain, context, tools, models, evidence, provenance, geospatial, permissions, cost, adapters, and evals.

## Consequences

- Fewer deployables and lower operating cost.
- Easier local development and testing.
- Future service extraction remains possible if evidence shows a real need.
- Microservices are deferred.

