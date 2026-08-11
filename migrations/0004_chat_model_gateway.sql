PRAGMA foreign_keys = ON;

ALTER TABLE model_runs ADD COLUMN prompt_id TEXT;
ALTER TABLE model_runs ADD COLUMN prompt_hash TEXT;
ALTER TABLE model_runs ADD COLUMN request_hash TEXT;
ALTER TABLE model_runs ADD COLUMN response_hash TEXT;
ALTER TABLE model_runs ADD COLUMN status TEXT NOT NULL DEFAULT 'success';
ALTER TABLE model_runs ADD COLUMN error TEXT;

CREATE TABLE IF NOT EXISTS prompt_harnesses (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    semantic_version TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    intended_task TEXT NOT NULL,
    model_compatibility TEXT NOT NULL DEFAULT '[]',
    output_schema TEXT NOT NULL DEFAULT '{}',
    evaluation_score REAL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (prompt_id, semantic_version, prompt_hash)
);

CREATE INDEX IF NOT EXISTS idx_prompt_harnesses_active
    ON prompt_harnesses (prompt_id, active, created_at);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    location_id TEXT,
    state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'archived')),
    last_message_at TEXT,
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, organization_id) REFERENCES workspaces(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (location_id, organization_id) REFERENCES locations(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_conversations_workspace
    ON conversations (organization_id, workspace_id, last_message_at, deleted_at);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'text',
    route TEXT,
    model_run_id TEXT,
    guidance_plan_id TEXT,
    source_record_ids TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    retention_policy TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (id, organization_id),
    FOREIGN KEY (conversation_id, organization_id) REFERENCES conversations(id, organization_id) ON DELETE CASCADE,
    FOREIGN KEY (model_run_id, organization_id) REFERENCES model_runs(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (guidance_plan_id, organization_id) REFERENCES guidance_plans(id, organization_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages (organization_id, conversation_id, created_at, deleted_at);
