PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS visual_analyses (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    user_plant_id TEXT,
    media_attachment_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    status TEXT NOT NULL CHECK (status IN ('AVAILABLE', 'UNAVAILABLE', 'PROVIDER_ERROR', 'VALIDATION_FAILED')),
    image_quality TEXT NOT NULL DEFAULT '{}',
    plant_candidates TEXT NOT NULL DEFAULT '[]',
    visual_observations TEXT NOT NULL DEFAULT '[]',
    visual_hypotheses TEXT NOT NULL DEFAULT '[]',
    required_next_evidence TEXT NOT NULL DEFAULT '[]',
    botanist_context TEXT NOT NULL DEFAULT '{}',
    geo_context_id TEXT,
    environmental_snapshot_id TEXT,
    model_run_id TEXT,
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    safety_notes TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (user_plant_id, organization_id) REFERENCES user_plants(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (media_attachment_id, organization_id) REFERENCES media_attachments(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (geo_context_id, organization_id) REFERENCES geo_contexts(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (environmental_snapshot_id, organization_id) REFERENCES environmental_snapshots(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (model_run_id, organization_id) REFERENCES model_runs(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_visual_analyses_plant
    ON visual_analyses (organization_id, user_plant_id, created_at, deleted_at);
