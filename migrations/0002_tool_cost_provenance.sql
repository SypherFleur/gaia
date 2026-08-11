PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usage_events (
    usage_event_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    workspace_id TEXT,
    provider_id TEXT NOT NULL,
    tool_id TEXT,
    model_id TEXT,
    request_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    usage_units REAL NOT NULL DEFAULT 0,
    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
    actual_cost_usd REAL,
    cache_hit INTEGER NOT NULL DEFAULT 0 CHECK (cache_hit IN (0, 1)),
    status TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_usage_events_org_provider_started
    ON usage_events (organization_id, provider_id, started_at);

CREATE INDEX IF NOT EXISTS idx_usage_events_request
    ON usage_events (request_id);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    actor_user_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    workspace_id TEXT,
    action TEXT NOT NULL,
    tool_id TEXT,
    provider_id TEXT,
    result TEXT NOT NULL,
    reason TEXT,
    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
    provenance_record_id TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_audit_events_org_created
    ON audit_events (organization_id, created_at);

CREATE TABLE IF NOT EXISTS cache_records (
    cache_key TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    stale_until TEXT,
    content_hash TEXT NOT NULL,
    provenance_reference TEXT,
    payload TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (cache_key, provider_id)
);

CREATE INDEX IF NOT EXISTS idx_cache_records_provider_expires
    ON cache_records (provider_id, expires_at);

CREATE TABLE IF NOT EXISTS source_snapshots (
    content_hash TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    canonical_url TEXT,
    license TEXT NOT NULL DEFAULT 'unknown',
    attribution TEXT,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    tenant_independent INTEGER NOT NULL DEFAULT 1 CHECK (tenant_independent IN (0, 1)),
    organization_id TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
);

