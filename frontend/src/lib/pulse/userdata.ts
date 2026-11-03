/**
 * A city's own data, kept in the browser. Only derived data is stored (a
 * boundary ring, a list of stations, daily counts), so a GTFS feed of tens of
 * megabytes becomes a few kilobytes. Nothing here is ever uploaded.
 *
 * Storage is localStorage under a versioned key. When the store is blocked
 * (private windows, quota, policies) the data lives in memory for the session.
 */
import type { Station } from "./import/types";
import type { Zone } from "./import/zones";

export interface CityData {
  version: 1;
  cityId: string;
  boundary?: { source: string; ring: [number, number][] };
  hubs?: { source: string; stations: Station[] };
  counts?: { source: string; rows: { station: string; dailyBoardings: number }[]; hourly?: number[] };
  /** Survey zones: residents and jobs per zone centroid replace the synthetic field. */
  zones?: { source: string; rows: Zone[] };
  loadedAt: string;
}

const PREFIX = "metropulse.citydata.";
const memory = new Map<string, string>();
/** Keys whose last write did not reach storage (quota, policy): the memory copy is the truth. */
const unsynced = new Set<string>();

export function cityDataStorageKey(cityId: string): string {
  return `${PREFIX}${cityId}.v1`;
}

function read(key: string): string | null {
  if (unsynced.has(key)) return memory.get(key) ?? null;
  try {
    const v = window.localStorage.getItem(key);
    if (v !== null) return v;
  } catch {
    /* blocked: fall through to memory */
  }
  return memory.get(key) ?? null;
}

function write(key: string, value: string | null): void {
  if (value === null) memory.delete(key);
  else memory.set(key, value);
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
    unsynced.delete(key);
  } catch {
    unsynced.add(key);
  }
}

export function loadCityData(cityId: string): CityData | null {
  const raw = read(cityDataStorageKey(cityId));
  if (!raw) return null;
  try {
    const d = JSON.parse(raw) as Partial<CityData>;
    if (d?.version !== 1 || d.cityId !== cityId) return null;
    return d as CityData;
  } catch {
    return null;
  }
}

export function saveCityData(data: CityData): void {
  write(cityDataStorageKey(data.cityId), JSON.stringify(data));
}

export function clearCityData(cityId: string): void {
  write(cityDataStorageKey(cityId), null);
}

function stable(v: unknown): string {
  if (Array.isArray(v)) return `[${v.map(stable).join(",")}]`;
  if (v && typeof v === "object") {
    const o = v as Record<string, unknown>;
    return `{${Object.keys(o)
      .filter((k) => o[k] !== undefined)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${stable(o[k])}`)
      .join(",")}}`;
  }
  return JSON.stringify(v);
}

/** Short stable hash (FNV-1a, 8 hex chars) of the data; "" for none. Used as a model cache key. */
export function cityDataKey(data: CityData | null | undefined): string {
  if (!data) return "";
  const s = stable(data);
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}

/** The status line: what was loaded and where it came from. */
export function describeCityData(data: CityData | null | undefined): string {
  if (!data) return "";
  const parts: string[] = [];
  if (data.boundary) parts.push(`Boundary: ${data.boundary.source}`);
  if (data.hubs) parts.push(`Stations: ${data.hubs.stations.length} from ${data.hubs.source}`);
  if (data.counts) {
    const n = data.counts.rows.length;
    parts.push(`Counts: ${n} station${n === 1 ? "" : "s"} from ${data.counts.source}${data.counts.hourly ? " (with hours)" : ""}`);
  }
  if (data.zones) parts.push(`Zones: ${data.zones.rows.length} from ${data.zones.source}`);
  return parts.join(" · ");
}
