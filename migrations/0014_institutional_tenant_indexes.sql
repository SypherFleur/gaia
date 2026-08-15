-- Phase 11-13 tenant-scoped tables shipped without indexes. Every list query in
-- packages/institutional filters by organization_id and orders by a timestamp,
-- so index those pairs, plus the parent keys used for collection/suite lookups.

CREATE INDEX IF NOT EXISTS idx_organization_policies_org ON organization_policies (organization_id, created_at);

CREATE INDEX IF NOT EXISTS idx_research_projects_org ON research_projects (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_research_projects_workspace ON research_projects (organization_id, workspace_id);

CREATE INDEX IF NOT EXISTS idx_research_runs_org ON research_runs (organization_id, started_at);
CREATE INDEX IF NOT EXISTS idx_research_runs_workspace ON research_runs (organization_id, workspace_id);

CREATE INDEX IF NOT EXISTS idx_reproducibility_bundles_org ON reproducibility_bundles (organization_id, created_at);

CREATE INDEX IF NOT EXISTS idx_model_comparisons_org ON model_comparisons (organization_id, created_at);

CREATE INDEX IF NOT EXISTS idx_evaluation_suites_org ON evaluation_suites (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_evaluation_cases_org ON evaluation_cases (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_evaluation_cases_suite ON evaluation_cases (organization_id, suite_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_org ON evaluation_runs (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_suite ON evaluation_runs (organization_id, suite_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_org ON evaluation_results (organization_id, created_at);

CREATE INDEX IF NOT EXISTS idx_human_reviews_org ON human_reviews (organization_id, created_at);

CREATE INDEX IF NOT EXISTS idx_datasets_org ON datasets (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_dataset_versions_org ON dataset_versions (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_dataset_versions_dataset ON dataset_versions (organization_id, dataset_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_collections_org ON knowledge_collections (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_org ON knowledge_documents (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_collection ON knowledge_documents (organization_id, collection_id);

CREATE INDEX IF NOT EXISTS idx_audit_exports_org ON audit_exports (organization_id, created_at);
