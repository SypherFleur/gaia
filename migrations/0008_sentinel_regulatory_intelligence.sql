PRAGMA foreign_keys = ON;

ALTER TABLE regulation_rules ADD COLUMN jurisdiction TEXT;
ALTER TABLE regulation_rules ADD COLUMN regulated_taxa TEXT NOT NULL DEFAULT '[]';
ALTER TABLE regulation_rules ADD COLUMN regulated_articles TEXT NOT NULL DEFAULT '[]';
ALTER TABLE regulation_rules ADD COLUMN plant_parts TEXT NOT NULL DEFAULT '[]';
ALTER TABLE regulation_rules ADD COLUMN exceptions TEXT NOT NULL DEFAULT '[]';
ALTER TABLE regulation_rules ADD COLUMN permits TEXT NOT NULL DEFAULT '[]';
ALTER TABLE regulation_rules ADD COLUMN treatments TEXT NOT NULL DEFAULT '[]';
ALTER TABLE regulation_rules ADD COLUMN inspection TEXT NOT NULL DEFAULT '[]';
ALTER TABLE regulation_rules ADD COLUMN reporting TEXT NOT NULL DEFAULT '[]';
ALTER TABLE regulation_rules ADD COLUMN authority_metadata TEXT NOT NULL DEFAULT '{}';
ALTER TABLE regulation_rules ADD COLUMN freshness TEXT NOT NULL DEFAULT 'UNAVAILABLE';
ALTER TABLE regulation_rules ADD COLUMN source_snapshot_reference TEXT;

CREATE TABLE IF NOT EXISTS movement_requests (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    origin_location_id TEXT,
    destination_location_id TEXT,
    planned_date TEXT,
    species TEXT,
    cultivar TEXT,
    plant_part TEXT NOT NULL DEFAULT 'unknown',
    live_plant INTEGER NOT NULL DEFAULT 0 CHECK (live_plant IN (0, 1)),
    soil_attached INTEGER NOT NULL DEFAULT 0 CHECK (soil_attached IN (0, 1)),
    growing_media TEXT,
    quantity INTEGER,
    purpose TEXT,
    commercial_or_personal TEXT NOT NULL DEFAULT 'personal',
    source_country TEXT,
    destination_country TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (origin_location_id, organization_id) REFERENCES locations(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (destination_location_id, organization_id) REFERENCES locations(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_movement_requests_workspace
    ON movement_requests (organization_id, workspace_id, created_at, deleted_at);

CREATE TABLE IF NOT EXISTS movement_decisions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    movement_request_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ALLOWED', 'CONDITIONAL', 'RESTRICTED', 'UNRESOLVED')),
    applicable_jurisdictions TEXT NOT NULL DEFAULT '[]',
    applicable_rules TEXT NOT NULL DEFAULT '[]',
    conditions TEXT NOT NULL DEFAULT '[]',
    permit_requirements TEXT NOT NULL DEFAULT '[]',
    treatment_requirements TEXT NOT NULL DEFAULT '[]',
    inspection_requirements TEXT NOT NULL DEFAULT '[]',
    reporting_requirements TEXT NOT NULL DEFAULT '[]',
    unresolved_questions TEXT NOT NULL DEFAULT '[]',
    conflicts TEXT NOT NULL DEFAULT '[]',
    checked_at TEXT NOT NULL,
    freshness TEXT NOT NULL CHECK (freshness IN ('CURRENT', 'STALE', 'EXPIRED', 'UNAVAILABLE', 'CONFLICT')),
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    model_run_ids TEXT NOT NULL DEFAULT '[]',
    authority_statement TEXT NOT NULL DEFAULT '',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (movement_request_id, organization_id) REFERENCES movement_requests(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_movement_decisions_request
    ON movement_decisions (organization_id, movement_request_id, checked_at, deleted_at);

CREATE TABLE IF NOT EXISTS sentinel_zone_features (
    id TEXT PRIMARY KEY,
    jurisdiction_pack TEXT NOT NULL,
    authority TEXT NOT NULL,
    zone_type TEXT NOT NULL,
    name TEXT NOT NULL,
    geometry_reference TEXT,
    area_scope TEXT NOT NULL DEFAULT '{}',
    effective_from TEXT,
    effective_to TEXT,
    source_record_id TEXT,
    freshness TEXT NOT NULL DEFAULT 'UNAVAILABLE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (source_record_id) REFERENCES source_records(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_sentinel_zone_features_pack
    ON sentinel_zone_features (jurisdiction_pack, zone_type, freshness, deleted_at);
