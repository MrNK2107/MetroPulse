-- Cloud workspaces (MetroPulse 2.1): a signed-in user's saved lines.
-- One row per line; the browser keeps a local copy and syncs both ways.

CREATE TABLE IF NOT EXISTS scenarios (
  id text PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  city_id text NOT NULL,
  name text NOT NULL,
  mode text NOT NULL CHECK (mode IN ('metro', 'brt', 'feeder')),
  alignment text NOT NULL CHECK (alignment IN ('elevated', 'underground', 'at-grade')),
  stations jsonb NOT NULL,
  costs jsonb,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS scenarios_user_city_idx ON scenarios (user_id, city_id);

ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;

-- Each user sees and edits only their own rows. The anon key alone cannot read anything.
DROP POLICY IF EXISTS scenarios_select_own ON scenarios;
CREATE POLICY scenarios_select_own ON scenarios FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS scenarios_insert_own ON scenarios;
CREATE POLICY scenarios_insert_own ON scenarios FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS scenarios_update_own ON scenarios;
CREATE POLICY scenarios_update_own ON scenarios FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS scenarios_delete_own ON scenarios;
CREATE POLICY scenarios_delete_own ON scenarios FOR DELETE USING (auth.uid() = user_id);
