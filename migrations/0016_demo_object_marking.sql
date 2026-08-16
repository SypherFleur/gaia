-- Seeded demo objects were indistinguishable from records the user created.
-- Locations already carried is_demo; plants and season plans did not, so a
-- sample tomato looked exactly like a real one. Mark them explicitly rather
-- than inferring from a workspace name.

ALTER TABLE user_plants ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1));
ALTER TABLE season_plans ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1));

CREATE INDEX IF NOT EXISTS idx_user_plants_demo ON user_plants (organization_id, is_demo);
CREATE INDEX IF NOT EXISTS idx_season_plans_demo ON season_plans (organization_id, is_demo);
