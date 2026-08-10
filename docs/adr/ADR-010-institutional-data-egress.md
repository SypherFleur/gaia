# ADR-010: Institutional Data Egress

Status: Accepted

## Context

Universities, governments, and sovereign deployments may have protected data, residency requirements, or private knowledge bases.

## Decision

Institutional and sovereign deployments must support local database, local object storage, local/private model runtime, configurable telemetry, audit export, and policy-controlled network egress. Protected content must not be sent to Cillian or remote model providers unless explicitly permitted by deployment policy.

## Consequences

- Model Gateway and Tool Gateway must check egress policy.
- Private images/documents are not used for global model improvement without agreement.
- Compliance certifications are not claimed until achieved.

