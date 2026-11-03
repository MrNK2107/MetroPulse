/**
 * Cloud workspaces: a signed-in user's lines live in a `scenarios` table (one row per line,
 * row-level security on user_id) and are mirrored into the local library. Local-first: the
 * desk works without a cloud, and sync only runs when someone is signed in.
 *
 * The store is a narrow interface so the sync logic is tested against an in-memory one and
 * production uses the Supabase adapter in supabase.ts.
 */
import type { Alignment, CostTable, Scenario } from "@/lib/pulse/scenario";
import type { ModeId } from "@/lib/pulse/siting";
import { listScenarios, putScenario } from "@/lib/pulse/scenarioStore";

export interface ScenarioRow {
  id: string;
  user_id: string;
  city_id: string;
  name: string;
  mode: ModeId;
  alignment: Alignment;
  stations: Scenario["stations"];
  costs: CostTable | null;
  notes: string | null;
  /** null for a personal line, else the team workspace it belongs to. */
  workspace_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CloudStore {
  /** Rows for a city in one scope: a workspace id, or null for the caller's personal lines. */
  list(cityId: string, workspaceId?: string | null): Promise<ScenarioRow[]>;
  upsert(rows: ScenarioRow[]): Promise<void>;
  remove(id: string): Promise<void>;
}

export function toRow(s: Scenario, userId: string): ScenarioRow {
  return {
    id: s.id,
    user_id: userId,
    city_id: s.cityId,
    name: s.name,
    mode: s.mode,
    alignment: s.alignment,
    stations: s.stations,
    costs: s.costs ?? null,
    notes: s.notes ?? null,
    workspace_id: s.workspaceId ?? null,
    created_at: s.createdAt,
    updated_at: s.updatedAt,
  };
}

export function fromRow(r: ScenarioRow): Scenario {
  return {
    id: r.id,
    cityId: r.city_id,
    name: r.name,
    mode: r.mode,
    alignment: r.alignment,
    stations: r.stations,
    ...(r.costs ? { costs: r.costs } : {}),
    ...(r.notes ? { notes: r.notes } : {}),
    ...(r.workspace_id ? { workspaceId: r.workspace_id } : {}),
    createdAt: r.created_at,
    updatedAt: r.updated_at,
  };
}

/** An in-memory store: the test double, and a handy stand-in for demos. */
export function memoryStore(initial: ScenarioRow[] = []): CloudStore {
  const rows = new Map(initial.map((r) => [r.id, r]));
  return {
    async list(cityId, workspaceId = null) {
      return Array.from(rows.values()).filter((r) => r.city_id === cityId && (r.workspace_id ?? null) === workspaceId);
    },
    async upsert(items) {
      for (const r of items) rows.set(r.id, r);
    },
    async remove(id) {
      rows.delete(id);
    },
  };
}

/**
 * Two-way merge by id within one scope (a workspace, or personal when null): the newer `updatedAt`
 * wins on both sides. Local lines tagged for other scopes are left alone.
 */
export async function syncScenarios(
  store: CloudStore,
  userId: string,
  cityId: string,
  workspaceId: string | null = null
): Promise<{ pulled: number; pushed: number }> {
  const cloud = new Map((await store.list(cityId, workspaceId)).map((r) => [r.id, r]));
  const local = new Map(
    listScenarios(cityId)
      .filter((s) => (s.workspaceId ?? null) === workspaceId)
      .map((s) => [s.id, s])
  );
  let pulled = 0;
  const toPush: ScenarioRow[] = [];
  for (const [id, row] of cloud) {
    const mine = local.get(id);
    if (!mine || mine.updatedAt < row.updated_at) {
      putScenario(fromRow(row));
      pulled++;
    } else if (mine.updatedAt > row.updated_at) {
      toPush.push(toRow(mine, userId));
    }
  }
  for (const [id, s] of local) if (!cloud.has(id)) toPush.push(toRow(s, userId));
  if (toPush.length) await store.upsert(toPush);
  return { pulled, pushed: toPush.length };
}
