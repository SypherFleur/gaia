PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('personal', 'community', 'university', 'government', 'business', 'ngo')),
    deployment_mode TEXT NOT NULL,
    default_country TEXT NOT NULL,
    default_units TEXT NOT NULL,
    data_retention_policy TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    external_auth_id TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    locale TEXT NOT NULL,
    timezone TEXT NOT NULL,
    default_units TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS memberships (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'researcher', 'extension_agent', 'grower', 'viewer')),
    permissions TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (organization_id, user_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    purpose TEXT NOT NULL,
    default_location_id TEXT,
    knowledge_policy TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS locations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    label TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    elevation_m REAL,
    accuracy_m REAL,
    privacy_precision TEXT NOT NULL DEFAULT 'approximate'
        CHECK (privacy_precision IN ('exact', 'approximate', '100m', '1km', 'county', 'district', 'custom')),
    exact_coordinates_authorized INTEGER NOT NULL DEFAULT 0 CHECK (exact_coordinates_authorized IN (0, 1)),
    timezone TEXT NOT NULL,
    country_code TEXT NOT NULL,
    admin1 TEXT,
    admin2 TEXT,
    county_fips TEXT,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_locations_org_country_admin
    ON locations (organization_id, country_code, admin1, admin2);

CREATE TABLE IF NOT EXISTS geo_contexts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    country TEXT,
    state_or_region TEXT,
    county_or_district TEXT,
    county_fips TEXT,
    hardiness_zone TEXT,
    ecoregion TEXT,
    watershed TEXT,
    climate_zone TEXT,
    regulatory_zones TEXT NOT NULL DEFAULT '[]',
    quarantine_zones TEXT NOT NULL DEFAULT '[]',
    pest_zones TEXT NOT NULL DEFAULT '[]',
    economic_regions TEXT NOT NULL DEFAULT '[]',
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (location_id, organization_id) REFERENCES locations(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS plant_entities (
    id TEXT PRIMARY KEY,
    scientific_name TEXT NOT NULL,
    canonical_taxon_id TEXT,
    common_names TEXT NOT NULL DEFAULT '[]',
    family TEXT,
    genus TEXT,
    species TEXT,
    subspecies TEXT,
    cultivar_optional TEXT,
    crop_group TEXT,
    source_ids TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_plant_entities_scientific_name
    ON plant_entities (scientific_name);

CREATE TABLE IF NOT EXISTS user_plants (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    plant_entity_id TEXT NOT NULL,
    nickname TEXT NOT NULL,
    cultivar TEXT,
    planted_at TEXT,
    acquired_at TEXT,
    lifecycle_stage TEXT,
    location_id TEXT,
    container_or_bed TEXT,
    status TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (location_id, organization_id) REFERENCES locations(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (plant_entity_id) REFERENCES plant_entities(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_user_plants_workspace
    ON user_plants (organization_id, workspace_id, deleted_at);

CREATE TABLE IF NOT EXISTS environmental_snapshots (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    observed_or_valid_at TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    temperature TEXT NOT NULL DEFAULT '{}',
    humidity TEXT NOT NULL DEFAULT '{}',
    precipitation TEXT NOT NULL DEFAULT '{}',
    wind TEXT NOT NULL DEFAULT '{}',
    pressure TEXT NOT NULL DEFAULT '{}',
    solar_radiation TEXT NOT NULL DEFAULT '{}',
    photoperiod TEXT NOT NULL DEFAULT '{}',
    soil_context TEXT NOT NULL DEFAULT '{}',
    soil_moisture_context TEXT NOT NULL DEFAULT '{}',
    drought_context TEXT NOT NULL DEFAULT '{}',
    water_context TEXT NOT NULL DEFAULT '{}',
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (location_id, organization_id) REFERENCES locations(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    user_plant_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    author_id TEXT NOT NULL,
    text TEXT NOT NULL,
    images TEXT NOT NULL DEFAULT '[]',
    audio TEXT NOT NULL DEFAULT '[]',
    video TEXT NOT NULL DEFAULT '[]',
    measurements TEXT NOT NULL DEFAULT '{}',
    weather_snapshot_id TEXT,
    source TEXT NOT NULL CHECK (source IN ('user', 'sensor', 'imported')),
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (user_plant_id, organization_id) REFERENCES user_plants(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (weather_snapshot_id, organization_id) REFERENCES environmental_snapshots(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_observations_plant
    ON observations (organization_id, user_plant_id, observed_at, deleted_at);

CREATE TABLE IF NOT EXISTS media_attachments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    observation_id TEXT,
    modality TEXT NOT NULL CHECK (modality IN ('image', 'audio', 'video', 'document_image')),
    storage_uri TEXT NOT NULL,
    content_type TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
    metadata TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (observation_id, organization_id) REFERENCES observations(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_media_workspace
    ON media_attachments (organization_id, workspace_id, modality, deleted_at);

CREATE TABLE IF NOT EXISTS source_records (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    provider TEXT NOT NULL,
    source_type TEXT NOT NULL,
    canonical_url TEXT,
    external_record_id TEXT,
    title TEXT NOT NULL,
    authority TEXT,
    retrieved_at TEXT NOT NULL,
    observed_at TEXT,
    valid_from TEXT,
    valid_to TEXT,
    license TEXT NOT NULL DEFAULT 'unknown',
    attribution TEXT,
    content_hash TEXT,
    raw_snapshot_reference TEXT,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_source_records_provider
    ON source_records (provider, source_type, retrieved_at);

CREATE TABLE IF NOT EXISTS evidence_claims (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    claim_text TEXT NOT NULL,
    evidence_grade TEXT NOT NULL CHECK (evidence_grade IN ('A', 'B', 'C', 'D', 'E')),
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    contradictory_source_ids TEXT NOT NULL DEFAULT '[]',
    generated_at TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS model_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    model_version TEXT,
    local_or_remote TEXT NOT NULL CHECK (local_or_remote IN ('local', 'remote')),
    input_modalities TEXT NOT NULL DEFAULT '[]',
    input_tokens_or_units INTEGER NOT NULL DEFAULT 0,
    output_tokens_or_units INTEGER NOT NULL DEFAULT 0,
    elapsed_ms INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0 CHECK (cost_usd >= 0.0),
    tool_calls TEXT NOT NULL DEFAULT '[]',
    prompt_version TEXT,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS guidance_plans (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    conversation_id TEXT,
    workspace_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    situation TEXT NOT NULL,
    recommendations TEXT NOT NULL DEFAULT '[]',
    actions TEXT NOT NULL DEFAULT '[]',
    timing TEXT NOT NULL DEFAULT '[]',
    resources TEXT NOT NULL DEFAULT '[]',
    evidence_claim_ids TEXT NOT NULL DEFAULT '[]',
    risks TEXT NOT NULL DEFAULT '[]',
    uncertainty TEXT NOT NULL DEFAULT '{}',
    measurements_to_take TEXT NOT NULL DEFAULT '[]',
    follow_up TEXT NOT NULL DEFAULT '[]',
    geo_context_id TEXT,
    environmental_snapshot_id TEXT,
    model_run_ids TEXT NOT NULL DEFAULT '[]',
    provenance_bundle_id TEXT,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (geo_context_id, organization_id) REFERENCES geo_contexts(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (environmental_snapshot_id, organization_id) REFERENCES environmental_snapshots(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_guidance_workspace
    ON guidance_plans (organization_id, workspace_id, created_at, deleted_at);

CREATE TABLE IF NOT EXISTS guidance_plan_evidence_claims (
    guidance_plan_id TEXT NOT NULL,
    evidence_claim_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    PRIMARY KEY (guidance_plan_id, evidence_claim_id),
    FOREIGN KEY (guidance_plan_id, organization_id) REFERENCES guidance_plans(id, organization_id) ON DELETE CASCADE,
    FOREIGN KEY (evidence_claim_id, organization_id) REFERENCES evidence_claims(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS guidance_plan_model_runs (
    guidance_plan_id TEXT NOT NULL,
    model_run_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    PRIMARY KEY (guidance_plan_id, model_run_id),
    FOREIGN KEY (guidance_plan_id, organization_id) REFERENCES guidance_plans(id, organization_id) ON DELETE CASCADE,
    FOREIGN KEY (model_run_id, organization_id) REFERENCES model_runs(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    guidance_plan_id TEXT NOT NULL,
    title TEXT NOT NULL,
    instructions TEXT NOT NULL,
    earliest_at TEXT,
    preferred_at TEXT,
    deadline TEXT,
    dependencies TEXT NOT NULL DEFAULT '[]',
    weather_sensitive INTEGER NOT NULL DEFAULT 0 CHECK (weather_sensitive IN (0, 1)),
    user_confirmation_required INTEGER NOT NULL DEFAULT 0 CHECK (user_confirmation_required IN (0, 1)),
    completion_status TEXT NOT NULL,
    completed_at TEXT,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (guidance_plan_id, organization_id) REFERENCES guidance_plans(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS outcomes (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    user_plant_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    result TEXT NOT NULL,
    measurements TEXT NOT NULL DEFAULT '{}',
    user_rating INTEGER,
    attachments TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (action_id, organization_id) REFERENCES actions(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (user_plant_id, organization_id) REFERENCES user_plants(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS regulation_rules (
    id TEXT PRIMARY KEY,
    jurisdiction_pack TEXT NOT NULL,
    authority TEXT NOT NULL,
    authority_level TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    regulated_article TEXT NOT NULL,
    pest_or_disease TEXT,
    geometry_or_area_reference TEXT,
    origin_scope TEXT NOT NULL DEFAULT '{}',
    destination_scope TEXT NOT NULL DEFAULT '{}',
    conditions TEXT NOT NULL DEFAULT '[]',
    permit_requirements TEXT NOT NULL DEFAULT '[]',
    treatment_requirements TEXT NOT NULL DEFAULT '[]',
    effective_from TEXT,
    effective_to TEXT,
    source_record_id TEXT,
    last_verified_at TEXT,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (source_record_id) REFERENCES source_records(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_regulation_rules_pack_article
    ON regulation_rules (jurisdiction_pack, regulated_article, effective_from, effective_to);

CREATE TABLE IF NOT EXISTS movement_checks (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    origin_geo_context_id TEXT NOT NULL,
    destination_geo_context_id TEXT NOT NULL,
    article TEXT NOT NULL,
    species TEXT,
    plant_part TEXT,
    soil_attached INTEGER NOT NULL DEFAULT 0 CHECK (soil_attached IN (0, 1)),
    purpose TEXT,
    planned_date TEXT,
    status TEXT NOT NULL CHECK (status IN ('allowed', 'conditional', 'restricted', 'unresolved')),
    applicable_rule_ids TEXT NOT NULL DEFAULT '[]',
    caveats TEXT NOT NULL DEFAULT '[]',
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    checked_at TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (origin_geo_context_id, organization_id) REFERENCES geo_contexts(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (destination_geo_context_id, organization_id) REFERENCES geo_contexts(id, organization_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS season_plans (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    crop_or_plant_ids TEXT NOT NULL DEFAULT '[]',
    objective TEXT NOT NULL,
    location_id TEXT,
    date_range TEXT NOT NULL DEFAULT '{}',
    tasks TEXT NOT NULL DEFAULT '[]',
    climate_basis TEXT NOT NULL DEFAULT '{}',
    forecast_basis TEXT NOT NULL DEFAULT '{}',
    regulatory_constraints TEXT NOT NULL DEFAULT '[]',
    market_context TEXT NOT NULL DEFAULT '[]',
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

CREATE TABLE IF NOT EXISTS calendar_bindings (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    external_calendar_id TEXT NOT NULL,
    encrypted_credential_reference TEXT NOT NULL,
    scopes TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (organization_id, user_id, provider, external_calendar_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);


