# Institution Deployment

GAIA Institution is a profile of the same GAIA core.

Recommended defaults:

- local or institution-approved models;
- provider allowlists;
- private document egress disabled unless explicitly approved;
- telemetry `LOCAL_ONLY` or `DISABLED`;
- dataset and project access controlled by workspace/project policy;
- JSON exports with SHA-256 hashes.

Internet-dependent features include live public provider adapters, remote model providers, remote embeddings, and calendar/OAuth workflows. Core stored-data queries, fixture/local context, local model reasoning, dataset registry, knowledge collections, reviews, and exports can operate locally.

This architecture includes controls intended to support future compliance work, but GAIA is not claiming FedRAMP, HIPAA, FERPA, SOC 2, ISO 27001, or other certification.

