PRAGMA foreign_keys = ON;

ALTER TABLE memberships ADD COLUMN project_permissions TEXT NOT NULL DEFAULT '{}';

ALTER TABLE research_annotations ADD COLUMN target_type TEXT NOT NULL DEFAULT 'paper';
ALTER TABLE research_annotations ADD COLUMN target_id TEXT;
ALTER TABLE research_annotations ADD COLUMN body TEXT;
ALTER TABLE research_annotations ADD COLUMN classification TEXT;
ALTER TABLE research_annotations ADD COLUMN visibility TEXT NOT NULL DEFAULT 'PRIVATE'
    CHECK (visibility IN ('PRIVATE', 'PROJECT', 'ORGANIZATION'));
ALTER TABLE research_annotations ADD COLUMN timestamp TEXT;

CREATE TABLE IF NOT EXISTS organization_policies (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL UNIQUE,
    deployment_mode TEXT NOT NULL DEFAULT 'local',
    location_precision_default TEXT NOT NULL DEFAULT '1km',
    telemetry_policy TEXT NOT NULL DEFAULT 'MINIMAL'
        CHECK (telemetry_policy IN ('MINIMAL', 'LOCAL_ONLY', 'DISABLED', 'CUSTOM')),
    model_policy TEXT NOT NULL DEFAULT '{}',
    tool_policy TEXT NOT NULL DEFAULT '{}',
    egress_policy TEXT NOT NULL DEFAULT '{}',
    export_policy TEXT NOT NULL DEFAULT '{}',
    data_sharing_policy TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS research_projects (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    research_question TEXT NOT NULL,
    principal_investigator TEXT,
    collaborators TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')),
    start_date TEXT,
    end_date TEXT,
    protocol_reference TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS research_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    research_project_id TEXT NOT NULL,
    initiated_by TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    query_or_task TEXT NOT NULL,
    input_bundle_id TEXT,
    context_bundle_id TEXT,
    model_run_ids TEXT NOT NULL DEFAULT '[]',
    tool_run_ids TEXT NOT NULL DEFAULT '[]',
    evidence_synthesis_ids TEXT NOT NULL DEFAULT '[]',
    guidance_plan_ids TEXT NOT NULL DEFAULT '[]',
    dataset_version_ids TEXT NOT NULL DEFAULT '[]',
    output_bundle_id TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'REVIEW_REQUIRED')),
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (research_project_id, organization_id) REFERENCES research_projects(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (initiated_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS reproducibility_bundles (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    research_run_id TEXT NOT NULL,
    source_records TEXT NOT NULL DEFAULT '[]',
    provider_versions TEXT NOT NULL DEFAULT '[]',
    context_snapshot TEXT NOT NULL DEFAULT '{}',
    input_hashes TEXT NOT NULL DEFAULT '{}',
    model_versions TEXT NOT NULL DEFAULT '[]',
    prompt_versions TEXT NOT NULL DEFAULT '[]',
    tool_versions TEXT NOT NULL DEFAULT '[]',
    calculation_versions TEXT NOT NULL DEFAULT '[]',
    evidence_records TEXT NOT NULL DEFAULT '[]',
    output_hashes TEXT NOT NULL DEFAULT '{}',
    environment_metadata TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (research_run_id, organization_id) REFERENCES research_runs(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS model_comparisons (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    input_bundle TEXT NOT NULL DEFAULT '{}',
    candidate_runs TEXT NOT NULL DEFAULT '[]',
    evaluation_results TEXT NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS evaluation_suites (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    cases TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS evaluation_cases (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    suite_id TEXT,
    prompt TEXT NOT NULL,
    expected_behavior TEXT NOT NULL,
    pass_fail_criteria TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (suite_id, organization_id) REFERENCES evaluation_suites(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    suite_id TEXT NOT NULL,
    model_version TEXT,
    harness_version TEXT,
    provider_configuration TEXT NOT NULL DEFAULT '{}',
    metrics TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'PENDING',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (suite_id, organization_id) REFERENCES evaluation_suites(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    evaluation_run_id TEXT NOT NULL,
    evaluation_case_id TEXT NOT NULL,
    metrics TEXT NOT NULL DEFAULT '{}',
    human_rating TEXT NOT NULL DEFAULT '{}',
    passed INTEGER NOT NULL DEFAULT 0 CHECK (passed IN (0, 1)),
    notes TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (evaluation_run_id, organization_id) REFERENCES evaluation_runs(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (evaluation_case_id, organization_id) REFERENCES evaluation_cases(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS human_reviews (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'UNREVIEWED'
        CHECK (review_status IN ('UNREVIEWED', 'REVIEWED', 'APPROVED', 'REJECTED', 'NEEDS_REVISION')),
    role TEXT NOT NULL DEFAULT 'reviewer',
    ratings TEXT NOT NULL DEFAULT '{}',
    body TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    owner TEXT NOT NULL,
    source TEXT NOT NULL,
    license TEXT NOT NULL,
    rights_status TEXT NOT NULL,
    sensitivity TEXT NOT NULL DEFAULT 'INTERNAL'
        CHECK (sensitivity IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED')),
    schema_reference TEXT,
    version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    schema_hash TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    source_provenance TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (dataset_id, organization_id, version),
    UNIQUE (id, organization_id),
    FOREIGN KEY (dataset_id, organization_id) REFERENCES datasets(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS knowledge_collections (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT,
    research_project_id TEXT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    visibility TEXT NOT NULL DEFAULT 'PRIVATE'
        CHECK (visibility IN ('PRIVATE', 'PROJECT', 'ORGANIZATION', 'PUBLIC')),
    retrieval_policy TEXT NOT NULL DEFAULT 'LOCAL_ONLY'
        CHECK (retrieval_policy IN ('LOCAL_ONLY', 'APPROVED_REMOTE', 'PUBLIC_ONLY')),
    embedding_policy TEXT NOT NULL DEFAULT '{}',
    egress_policy TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (research_project_id, organization_id) REFERENCES research_projects(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT,
    collection_id TEXT NOT NULL,
    title TEXT NOT NULL,
    format TEXT NOT NULL,
    body TEXT NOT NULL,
    chunks TEXT NOT NULL DEFAULT '[]',
    rights_status TEXT NOT NULL,
    sensitivity TEXT NOT NULL DEFAULT 'INTERNAL'
        CHECK (sensitivity IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED')),
    source_record_id TEXT,
    content_hash TEXT NOT NULL,
    untrusted_content INTEGER NOT NULL DEFAULT 1 CHECK (untrusted_content IN (0, 1)),
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (collection_id, organization_id) REFERENCES knowledge_collections(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (source_record_id) REFERENCES source_records(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS audit_exports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    generated_by TEXT NOT NULL,
    date_range TEXT NOT NULL DEFAULT '{}',
    event_classes TEXT NOT NULL DEFAULT '[]',
    format TEXT NOT NULL DEFAULT 'json',
    content_hash TEXT NOT NULL,
    manifest TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (generated_by) REFERENCES users(id) ON DELETE RESTRICT
);

