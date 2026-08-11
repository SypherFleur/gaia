PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS research_authors (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    given_name TEXT,
    family_name TEXT,
    orcid TEXT,
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_research_authors_orcid
    ON research_authors (orcid);

CREATE TABLE IF NOT EXISTS research_works (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    publication_year INTEGER,
    journal TEXT,
    doi TEXT,
    pmid TEXT,
    pmcid TEXT,
    provider_ids TEXT NOT NULL DEFAULT '{}',
    publication_types TEXT NOT NULL DEFAULT '[]',
    open_access_status TEXT NOT NULL DEFAULT 'unknown',
    retracted_status TEXT NOT NULL DEFAULT 'unknown',
    study_type TEXT NOT NULL DEFAULT 'unknown',
    authors TEXT NOT NULL DEFAULT '[]',
    evidence_policy TEXT NOT NULL DEFAULT '{}',
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_research_works_doi
    ON research_works (doi)
    WHERE doi IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_research_works_pmid
    ON research_works (pmid)
    WHERE pmid IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_research_works_provider_ids
    ON research_works (created_at, deleted_at);

CREATE TABLE IF NOT EXISTS research_claims (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    statement TEXT NOT NULL,
    subject TEXT NOT NULL,
    evidence_direction TEXT NOT NULL CHECK (evidence_direction IN ('supporting', 'contradictory', 'uncertain', 'irrelevant')),
    evidence_quality TEXT NOT NULL DEFAULT 'unknown',
    evidence_grade TEXT NOT NULL CHECK (evidence_grade IN ('A', 'B', 'C', 'D', 'E')),
    model_confidence TEXT,
    data_freshness TEXT NOT NULL DEFAULT 'unknown',
    source_work_ids TEXT NOT NULL DEFAULT '[]',
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    limitations TEXT NOT NULL DEFAULT '[]',
    study_type TEXT NOT NULL DEFAULT 'unknown',
    applicability TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_research_claims_org_direction
    ON research_claims (organization_id, evidence_direction, created_at, deleted_at);

CREATE TABLE IF NOT EXISTS evidence_syntheses (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    question TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT '{}',
    supporting_claims TEXT NOT NULL DEFAULT '[]',
    contradictory_claims TEXT NOT NULL DEFAULT '[]',
    uncertain_claims TEXT NOT NULL DEFAULT '[]',
    evidence_quality TEXT NOT NULL DEFAULT 'unknown',
    model_confidence TEXT,
    data_freshness TEXT NOT NULL DEFAULT 'unknown',
    uncertainty TEXT NOT NULL DEFAULT '{}',
    applicability TEXT NOT NULL DEFAULT '{}',
    source_work_ids TEXT NOT NULL DEFAULT '[]',
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    model_run_ids TEXT NOT NULL DEFAULT '[]',
    provenance_bundle_id TEXT,
    export_payload TEXT NOT NULL DEFAULT '{}',
    generated_at TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_evidence_syntheses_workspace
    ON evidence_syntheses (organization_id, workspace_id, generated_at, deleted_at);

CREATE TABLE IF NOT EXISTS research_collections (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    visibility TEXT NOT NULL DEFAULT 'private' CHECK (visibility IN ('private', 'institution', 'public')),
    work_ids TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_research_collections_workspace
    ON research_collections (organization_id, workspace_id, visibility, deleted_at);

CREATE TABLE IF NOT EXISTS research_annotations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    collection_id TEXT,
    work_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    note TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    private INTEGER NOT NULL DEFAULT 1 CHECK (private IN (0, 1)),
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (collection_id, organization_id) REFERENCES research_collections(id, organization_id) ON DELETE SET NULL,
    FOREIGN KEY (work_id) REFERENCES research_works(id) ON DELETE RESTRICT,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_research_annotations_workspace
    ON research_annotations (organization_id, workspace_id, work_id, deleted_at);
