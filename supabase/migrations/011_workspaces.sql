-- Team workspaces (MetroPulse 2.2): shared libraries of lines with owner / editor / viewer roles.
-- Membership is by email so a planner can be invited before their first sign-in; the row is
-- matched to auth.email() at query time.

CREATE TABLE IF NOT EXISTS workspaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  owner_id uuid NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspace_members (
  workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
  email text NOT NULL,
  user_id uuid REFERENCES auth.users (id) ON DELETE SET NULL,
  role text NOT NULL CHECK (role IN ('owner', 'editor', 'viewer')),
  invited_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, email)
);

ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces (id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS scenarios_workspace_city_idx ON scenarios (workspace_id, city_id);

-- Helper: the caller's role in a workspace, by user id or by invited email.
CREATE OR REPLACE FUNCTION workspace_role(ws uuid) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT m.role FROM workspace_members m
  WHERE m.workspace_id = ws
    AND (m.user_id = auth.uid() OR lower(m.email) = lower(coalesce(auth.email(), '')))
  LIMIT 1
$$;

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS workspaces_member_select ON workspaces;
CREATE POLICY workspaces_member_select ON workspaces FOR SELECT USING (workspace_role(id) IS NOT NULL);
DROP POLICY IF EXISTS workspaces_owner_insert ON workspaces;
CREATE POLICY workspaces_owner_insert ON workspaces FOR INSERT WITH CHECK (auth.uid() = owner_id);
DROP POLICY IF EXISTS workspaces_owner_update ON workspaces;
CREATE POLICY workspaces_owner_update ON workspaces FOR UPDATE USING (auth.uid() = owner_id);
DROP POLICY IF EXISTS workspaces_owner_delete ON workspaces;
CREATE POLICY workspaces_owner_delete ON workspaces FOR DELETE USING (auth.uid() = owner_id);

DROP POLICY IF EXISTS members_select ON workspace_members;
CREATE POLICY members_select ON workspace_members FOR SELECT USING (workspace_role(workspace_id) IS NOT NULL);
DROP POLICY IF EXISTS members_owner_write ON workspace_members;
CREATE POLICY members_owner_write ON workspace_members FOR ALL
  USING (workspace_role(workspace_id) = 'owner' OR (SELECT owner_id FROM workspaces w WHERE w.id = workspace_id) = auth.uid())
  WITH CHECK (workspace_role(workspace_id) = 'owner' OR (SELECT owner_id FROM workspaces w WHERE w.id = workspace_id) = auth.uid());

-- Scenarios: personal rows stay user-scoped (migration 010); workspace rows are member-scoped.
DROP POLICY IF EXISTS scenarios_select_own ON scenarios;
CREATE POLICY scenarios_select_own ON scenarios FOR SELECT
  USING ((workspace_id IS NULL AND auth.uid() = user_id) OR (workspace_id IS NOT NULL AND workspace_role(workspace_id) IS NOT NULL));
DROP POLICY IF EXISTS scenarios_insert_own ON scenarios;
CREATE POLICY scenarios_insert_own ON scenarios FOR INSERT
  WITH CHECK ((workspace_id IS NULL AND auth.uid() = user_id) OR (workspace_id IS NOT NULL AND workspace_role(workspace_id) IN ('owner', 'editor')));
DROP POLICY IF EXISTS scenarios_update_own ON scenarios;
CREATE POLICY scenarios_update_own ON scenarios FOR UPDATE
  USING ((workspace_id IS NULL AND auth.uid() = user_id) OR (workspace_id IS NOT NULL AND workspace_role(workspace_id) IN ('owner', 'editor')))
  WITH CHECK ((workspace_id IS NULL AND auth.uid() = user_id) OR (workspace_id IS NOT NULL AND workspace_role(workspace_id) IN ('owner', 'editor')));
DROP POLICY IF EXISTS scenarios_delete_own ON scenarios;
CREATE POLICY scenarios_delete_own ON scenarios FOR DELETE
  USING ((workspace_id IS NULL AND auth.uid() = user_id) OR (workspace_id IS NOT NULL AND workspace_role(workspace_id) IN ('owner', 'editor')));
