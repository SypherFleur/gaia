# ADR-004: Provenance Model

Status: Accepted

## Context

GAIA recommendations must answer where claims came from, what data was used, when it was retrieved, and which model/tool versions participated.

## Decision

Every external datum uses a provenance envelope and persists source metadata. Guidance uses `EvidenceClaim`, `SourceRecord`, `ModelRun`, and future `ProvenanceBundle` records.

## Consequences

- LLMs may phrase recommendations but may not fabricate evidence objects.
- Research and institution users can export auditable bundles.
- Hidden chain-of-thought is not exposed.

