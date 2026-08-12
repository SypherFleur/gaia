# Institutional Architecture

Phase 11 strengthens GAIA for university, extension, NGO, government, and regulated-organization use without forking the platform.

The structure is:

```text
Organization
|- Members
|- Roles / Permissions
|- Organization Policy
|- Workspaces
|  |- Grower workspace
|  |- Research workspace
|  |- Extension workspace
|  `- Analysis workspace
|- Knowledge Collections
|- Datasets
|- Research Projects
`- Exports / Audit
```

GAIA Public, GAIA Institution, and GAIA Sovereign are deployment profiles of the same core platform. They differ through deployment mode, organization policy, provider configuration, egress policy, telemetry policy, and permissions.

Phase 11 introduces `ResearchProject`, `ResearchRun`, `ReproducibilityBundle`, `Dataset`, `DatasetVersion`, `KnowledgeCollection`, `KnowledgeDocument`, `HumanReview`, `ModelComparison`, evaluation objects, `AuditExport`, and `OrganizationPolicy`.

The implementation is local/SQLite friendly and fixture-first. No paid IAM, vector database, observability platform, storage tier, model, or search cluster is required.

