PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS mercator_contexts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    location_id TEXT,
    commodity TEXT NOT NULL DEFAULT '{}',
    crop_or_taxon TEXT NOT NULL DEFAULT '{}',
    geography TEXT NOT NULL DEFAULT '{}',
    production_statistics TEXT NOT NULL DEFAULT '[]',
    market_reports TEXT NOT NULL DEFAULT '[]',
    price_observations TEXT NOT NULL DEFAULT '[]',
    regional_economic_context TEXT NOT NULL DEFAULT '[]',
    supply_chain_context TEXT NOT NULL DEFAULT '[]',
    data_dates TEXT NOT NULL DEFAULT '{}',
    freshness TEXT NOT NULL DEFAULT '{}',
    provider_statuses TEXT NOT NULL DEFAULT '{}',
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    limitations TEXT NOT NULL DEFAULT '[]',
    generated_at TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (location_id, organization_id) REFERENCES locations(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_mercator_contexts_workspace
    ON mercator_contexts (organization_id, workspace_id, generated_at, deleted_at);

CREATE INDEX IF NOT EXISTS idx_mercator_contexts_location
    ON mercator_contexts (organization_id, location_id, generated_at, deleted_at);

