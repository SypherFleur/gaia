PRAGMA foreign_keys = ON;

ALTER TABLE plant_entities ADD COLUMN kingdom TEXT;
ALTER TABLE plant_entities ADD COLUMN edible_classification TEXT;
ALTER TABLE plant_entities ADD COLUMN native_status TEXT;
ALTER TABLE plant_entities ADD COLUMN introduced_status TEXT;
ALTER TABLE plant_entities ADD COLUMN synonyms TEXT NOT NULL DEFAULT '[]';
ALTER TABLE plant_entities ADD COLUMN external_source_ids TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_entities ADD COLUMN canonical_name_source_record_id TEXT;

ALTER TABLE user_plants ADD COLUMN growing_method TEXT;
ALTER TABLE user_plants ADD COLUMN biocube_reference TEXT;
ALTER TABLE user_plants ADD COLUMN notes TEXT NOT NULL DEFAULT '';
ALTER TABLE user_plants ADD COLUMN tags TEXT NOT NULL DEFAULT '[]';
ALTER TABLE user_plants ADD COLUMN archived_at TEXT;

ALTER TABLE observations ADD COLUMN observed_facts TEXT NOT NULL DEFAULT '[]';
ALTER TABLE observations ADD COLUMN gaia_inferences TEXT NOT NULL DEFAULT '[]';
ALTER TABLE observations ADD COLUMN lifecycle_stage_observed TEXT;
ALTER TABLE observations ADD COLUMN health_tags TEXT NOT NULL DEFAULT '[]';
ALTER TABLE observations ADD COLUMN action_id TEXT;
ALTER TABLE observations ADD COLUMN outcome_id TEXT;

ALTER TABLE conversations ADD COLUMN user_plant_id TEXT;
ALTER TABLE guidance_plans ADD COLUMN user_plant_id TEXT;

CREATE TABLE IF NOT EXISTS plant_profiles (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    plant_entity_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    taxonomy TEXT NOT NULL DEFAULT '{}',
    common_names TEXT NOT NULL DEFAULT '[]',
    crop_group TEXT,
    growth_habit TEXT,
    lifecycle TEXT,
    temperature_context TEXT NOT NULL DEFAULT '{}',
    water_context TEXT NOT NULL DEFAULT '{}',
    soil_context TEXT NOT NULL DEFAULT '{}',
    light_context TEXT NOT NULL DEFAULT '{}',
    season_context TEXT NOT NULL DEFAULT '{}',
    known_pest_links TEXT NOT NULL DEFAULT '[]',
    known_disease_links TEXT NOT NULL DEFAULT '[]',
    germplasm_links TEXT NOT NULL DEFAULT '[]',
    field_provenance TEXT NOT NULL DEFAULT '{}',
    conflicts TEXT NOT NULL DEFAULT '[]',
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    confidence TEXT NOT NULL DEFAULT '{}',
    completeness REAL NOT NULL DEFAULT 0.0 CHECK (completeness >= 0.0 AND completeness <= 1.0),
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (plant_entity_id) REFERENCES plant_entities(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_plant_profiles_entity
    ON plant_profiles (organization_id, plant_entity_id, version, deleted_at);
