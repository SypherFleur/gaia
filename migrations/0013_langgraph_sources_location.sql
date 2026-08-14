PRAGMA foreign_keys = ON;

ALTER TABLE locations ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'saved'
    CHECK (source_kind IN ('device', 'manual', 'saved', 'demo_fixture'));
ALTER TABLE locations ADD COLUMN source_label TEXT;
ALTER TABLE locations ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1));
ALTER TABLE locations ADD COLUMN verified_at TEXT;
