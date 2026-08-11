PRAGMA foreign_keys = ON;

ALTER TABLE geo_contexts ADD COLUMN country_code TEXT;
ALTER TABLE geo_contexts ADD COLUMN state_code TEXT;
ALTER TABLE geo_contexts ADD COLUMN timezone TEXT;
ALTER TABLE geo_contexts ADD COLUMN elevation_m REAL;

ALTER TABLE environmental_snapshots ADD COLUMN forecast TEXT NOT NULL DEFAULT '{}';
ALTER TABLE environmental_snapshots ADD COLUMN solar_context TEXT NOT NULL DEFAULT '{}';
ALTER TABLE environmental_snapshots ADD COLUMN season_context TEXT NOT NULL DEFAULT '{}';
ALTER TABLE environmental_snapshots ADD COLUMN astronomical_context TEXT NOT NULL DEFAULT '{}';
ALTER TABLE environmental_snapshots ADD COLUMN provider_statuses TEXT NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS atlas_zone_features (
    id TEXT PRIMARY KEY,
    zone_type TEXT NOT NULL CHECK (zone_type IN ('jurisdiction', 'quarantine', 'pest', 'regulatory', 'economic')),
    name TEXT NOT NULL,
    authority TEXT NOT NULL,
    jurisdiction_pack TEXT,
    effective_from TEXT,
    effective_to TEXT,
    geometry_reference TEXT,
    source_record_id TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_record_id) REFERENCES source_records(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_atlas_zone_features_type_authority
    ON atlas_zone_features (zone_type, authority, effective_from, effective_to);
