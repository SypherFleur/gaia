PRAGMA foreign_keys = OFF;

ALTER TABLE season_plans ADD COLUMN name TEXT NOT NULL DEFAULT '';
ALTER TABLE season_plans ADD COLUMN start_date TEXT;
ALTER TABLE season_plans ADD COLUMN end_date TEXT;
ALTER TABLE season_plans ADD COLUMN planning_basis TEXT NOT NULL DEFAULT '{}';
ALTER TABLE season_plans ADD COLUMN status TEXT NOT NULL DEFAULT 'draft';
ALTER TABLE season_plans ADD COLUMN confidence TEXT NOT NULL DEFAULT 'PROVISIONAL';
ALTER TABLE season_plans ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE season_plans ADD COLUMN supersedes_plan_id TEXT;

ALTER TABLE outcomes ADD COLUMN planned_at TEXT;
ALTER TABLE outcomes ADD COLUMN actual_at TEXT;
ALTER TABLE outcomes ADD COLUMN environment_snapshot_id TEXT;

CREATE TABLE IF NOT EXISTS actions_new (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    guidance_plan_id TEXT,
    season_plan_id TEXT,
    plant_or_crop_id TEXT,
    title TEXT NOT NULL,
    instructions TEXT NOT NULL,
    action_type TEXT NOT NULL DEFAULT 'custom',
    earliest_at TEXT,
    preferred_at TEXT,
    deadline TEXT,
    latest_at TEXT,
    duration_minutes INTEGER,
    recurrence TEXT NOT NULL DEFAULT '{}',
    dependencies TEXT NOT NULL DEFAULT '[]',
    weather_sensitive INTEGER NOT NULL DEFAULT 0 CHECK (weather_sensitive IN (0, 1)),
    environmental_conditions TEXT NOT NULL DEFAULT '[]',
    regulatory_conditions TEXT NOT NULL DEFAULT '[]',
    user_confirmation_required INTEGER NOT NULL DEFAULT 0 CHECK (user_confirmation_required IN (0, 1)),
    calendar_binding TEXT NOT NULL DEFAULT '{}',
    completion_status TEXT NOT NULL DEFAULT 'NOT_STARTED'
        CHECK (completion_status IN ('NOT_STARTED', 'DONE', 'SKIPPED', 'PARTIAL', 'FAILED', 'pending')),
    completed_at TEXT,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    CHECK (guidance_plan_id IS NOT NULL OR season_plan_id IS NOT NULL),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (guidance_plan_id, organization_id) REFERENCES guidance_plans(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (season_plan_id, organization_id) REFERENCES season_plans(id, organization_id) ON DELETE RESTRICT
);

INSERT INTO actions_new (
    id, organization_id, guidance_plan_id, title, instructions,
    earliest_at, preferred_at, deadline, dependencies, weather_sensitive,
    user_confirmation_required, completion_status, completed_at,
    retention_policy, created_at, updated_at, deleted_at
)
SELECT
    id, organization_id, guidance_plan_id, title, instructions,
    earliest_at, preferred_at, deadline, dependencies, weather_sensitive,
    user_confirmation_required,
    CASE completion_status WHEN 'pending' THEN 'NOT_STARTED' ELSE completion_status END,
    completed_at, retention_policy, created_at, updated_at, deleted_at
FROM actions;

DROP TABLE actions;
ALTER TABLE actions_new RENAME TO actions;

CREATE INDEX IF NOT EXISTS idx_actions_season_plan
    ON actions (organization_id, season_plan_id, preferred_at, deleted_at);

CREATE TABLE IF NOT EXISTS season_plan_revisions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    previous_plan_id TEXT NOT NULL,
    revised_plan_id TEXT,
    reason TEXT NOT NULL,
    changed_actions TEXT NOT NULL DEFAULT '[]',
    unchanged_actions TEXT NOT NULL DEFAULT '[]',
    context_change TEXT NOT NULL DEFAULT '{}',
    generated_at TEXT NOT NULL,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (previous_plan_id, organization_id) REFERENCES season_plans(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (revised_plan_id, organization_id) REFERENCES season_plans(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_season_plan_revisions_previous
    ON season_plan_revisions (organization_id, previous_plan_id, generated_at, deleted_at);

ALTER TABLE calendar_bindings ADD COLUMN credential_reference TEXT;
ALTER TABLE calendar_bindings ADD COLUMN status TEXT NOT NULL DEFAULT 'connected';
ALTER TABLE calendar_bindings ADD COLUMN revoked_at TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_calendar_bindings_id_org
    ON calendar_bindings (id, organization_id);

CREATE TABLE IF NOT EXISTS calendar_previews (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    season_plan_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    calendar_binding_id TEXT NOT NULL,
    event_previews TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'preview',
    expires_at TEXT,
    committed_at TEXT,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (season_plan_id, organization_id) REFERENCES season_plans(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (calendar_binding_id, organization_id) REFERENCES calendar_bindings(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_calendar_previews_plan
    ON calendar_previews (organization_id, season_plan_id, plan_version, status, deleted_at);

CREATE TABLE IF NOT EXISTS calendar_event_bindings (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    calendar_binding_id TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    last_synced_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (organization_id, action_id, calendar_binding_id, plan_version),
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (action_id, organization_id) REFERENCES actions(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (calendar_binding_id, organization_id) REFERENCES calendar_bindings(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_calendar_event_bindings_action
    ON calendar_event_bindings (organization_id, action_id, status, deleted_at);

PRAGMA foreign_keys = ON;
