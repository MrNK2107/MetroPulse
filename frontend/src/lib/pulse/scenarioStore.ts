/**
 * The scenario library: saved lines, kept in this browser. Same storage rule
 * as the city data store: localStorage under a versioned key, with an
 * in-memory copy for the session when the store is blocked.
 */
import { newScenarioId, Scenario } from "./scenario";

const KEY = "metropulse.scenarios.v1";
const MODES = new Set(["metro", "brt", "feeder"]);
const ALIGNMENTS = new Set(["elevated", "underground", "at-grade"]);

/** The last list written this session; the answer only while storage cannot take or give it. */
let memory: Scenario[] = [];
let unsynced = false;

function readAll(): Scenario[] {
  if (unsynced) return memory;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const d = JSON.parse(raw) as { version?: number; scenarios?: unknown[] };
    if (d?.version === 1 && Array.isArray(d.scenarios)) return d.scenarios.filter(isScenario);
    return [];
  } catch {
    /* blocked or corrupt: what this session wrote */
    return memory;
  }
}

function writeAll(list: Scenario[]): void {
  memory = list;
  try {
    window.localStorage.setItem(KEY, JSON.stringify({ version: 1, scenarios: list }));
    unsynced = false;
  } catch {
    unsynced = true; // the memory copy is the truth until a write succeeds
  }
}

function isScenario(x: unknown): x is Scenario {
  if (!x || typeof x !== "object") return false;
  const s = x as Partial<Scenario>;
  return (
    typeof s.id === "string" &&
    typeof s.cityId === "string" &&
    typeof s.name === "string" &&
    MODES.has(s.mode as string) &&
    ALIGNMENTS.has(s.alignment as string) &&
    Array.isArray(s.stations) &&
    s.stations.length >= 1 &&
    s.stations.every((p) => p && Number.isFinite(p.lat) && Number.isFinite(p.lng)) &&
    typeof s.createdAt === "string" &&
    typeof s.updatedAt === "string" &&
    (s.workspaceId === undefined || typeof s.workspaceId === "string")
  );
}

/** Newest first. */
export function listScenarios(cityId?: string): Scenario[] {
  // Newest first; a tie (two saves in the same millisecond) keeps the later save first.
  return readAll()
    .map((s, k) => ({ s, k }))
    .filter(({ s }) => !cityId || s.cityId === cityId)
    .sort((a, b) => (a.s.updatedAt < b.s.updatedAt ? 1 : a.s.updatedAt > b.s.updatedAt ? -1 : b.k - a.k))
    .map(({ s }) => s);
}

/** With a cityId, a line saved for another city is not returned (it would be scored on the wrong model). */
export function getScenario(id: string, cityId?: string): Scenario | null {
  const s = readAll().find((x) => x.id === id) ?? null;
  return s && (!cityId || s.cityId === cityId) ? s : null;
}

/** Upsert by id; `updatedAt` is set to now. */
export function saveScenario(s: Scenario): void {
  const list = readAll().filter((x) => x.id !== s.id);
  list.push({ ...s, updatedAt: new Date().toISOString() });
  writeAll(list);
}

/** Upsert without touching `updatedAt`: for copies that arrive with their own timestamp (cloud sync, imports). */
export function putScenario(s: Scenario): void {
  const list = readAll().filter((x) => x.id !== s.id);
  list.push({ ...s });
  writeAll(list);
}

export function removeScenario(id: string): void {
  writeAll(readAll().filter((s) => s.id !== id));
}

export function exportScenarios(cityId?: string): string {
  return JSON.stringify({ version: 1, scenarios: listScenarios(cityId) }, null, 2);
}

/** Adds the scenarios in the JSON; ids that collide with saved ones are regenerated. */
export function importScenarios(json: string, opts: { replace?: boolean } = {}): { added: number; error?: string } {
  let d: { version?: number; scenarios?: unknown[] };
  try {
    d = JSON.parse(json);
  } catch {
    return { added: 0, error: "Not valid JSON" };
  }
  if (!d || d.version !== 1) return { added: 0, error: "Unsupported file version (expected 1)" };
  if (!Array.isArray(d.scenarios)) return { added: 0, error: "No scenarios list in this file" };
  const bad = d.scenarios.find((s) => !isScenario(s));
  if (bad) return { added: 0, error: "A scenario is missing its stations or has an unknown mode" };
  const existing = opts.replace ? [] : readAll().slice();
  const ids = new Set(existing.map((s) => s.id));
  let added = 0;
  for (const s of d.scenarios as Scenario[]) {
    let id = s.id;
    while (ids.has(id)) id = newScenarioId();
    ids.add(id);
    existing.push({ ...s, id });
    added++;
  }
  writeAll(existing);
  return { added };
}
