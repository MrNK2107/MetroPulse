import type {
  BoundaryLevel,
  Observation,
  PlaceDetail,
  PlaceMatch,
  Receipt,
  Resolution,
} from "@/types/twin";

const base = () => process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getEnvelope(path: string): Promise<{ data: any; meta: any }> {
  const res = await fetch(`${base()}${path}`);
  let body: any = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON error body */
  }
  if (!res.ok || !body || body.success === false) {
    throw new Error(body?.error || `Request failed (${res.status})`);
  }
  return { data: body.data, meta: body.meta };
}

const toMatch = (m: any): PlaceMatch => ({
  placeId: m.place_id,
  name: m.name,
  level: m.level,
  stateCode: m.state_code ?? null,
  score: m.score,
  method: m.method,
});

const toReceipt = (r: any): Receipt => ({
  sourceId: r.source_id,
  sourceName: r.source_name,
  datasetVersion: r.dataset_version ?? null,
  license: r.license ?? null,
  url: r.url ?? null,
});

export async function resolvePlace(
  q: string,
  opts: { level?: string; state?: string } = {}
): Promise<Resolution> {
  const p = new URLSearchParams({ q });
  if (opts.level) p.set("level", opts.level);
  if (opts.state) p.set("state", opts.state);
  const { data } = await getEnvelope(`/api/twin/places/resolve?${p}`);
  return { matches: (data.matches ?? []).map(toMatch), ambiguous: !!data.ambiguous };
}

export async function getPlace(id: string): Promise<PlaceDetail> {
  const { data } = await getEnvelope(`/api/twin/places/${encodeURIComponent(id)}`);
  const ref = (x: any) => (x ? { placeId: x.place_id, name: x.name } : null);
  return {
    placeId: data.place_id,
    name: data.name,
    level: data.level,
    parent: ref(data.parent),
    state: ref(data.state),
  };
}

export async function getObservations(id: string): Promise<Observation[]> {
  const { data } = await getEnvelope(
    `/api/twin/places/${encodeURIComponent(id)}/observations`
  );
  return (data as any[]).map((o) => ({
    indicator: o.indicator,
    name: o.name,
    unit: o.unit,
    period: o.period ?? null,
    value: o.value ?? null,
    trustLabel: o.trust_label ?? null,
    receipt: toReceipt(o.receipt),
  }));
}

export function boundariesUrl(level: BoundaryLevel): string {
  return `${base()}/api/twin/boundaries/${level}`;
}

export type BoundaryCollection = { type?: string; features: any[] };

const boundaryCache = new Map<BoundaryLevel, Promise<BoundaryCollection>>();
const MAX_RETRY_AFTER_MS = 30_000;

function retryAfterMs(res: Response): number {
  const raw = res.headers?.get?.("retry-after");
  const secs = raw == null ? NaN : Number(raw);
  if (Number.isFinite(secs) && secs >= 0) return Math.min(secs * 1000, MAX_RETRY_AFTER_MS);
  const date = raw ? Date.parse(raw) : NaN;
  if (Number.isFinite(date)) return Math.min(Math.max(date - Date.now(), 0), MAX_RETRY_AFTER_MS);
  return 1000;
}

async function fetchBoundaries(level: BoundaryLevel): Promise<BoundaryCollection> {
  let res = await fetch(boundariesUrl(level));
  if (res.status === 429) {
    // One retry, after the server's Retry-After, before giving up.
    await new Promise((resolve) => setTimeout(resolve, retryAfterMs(res)));
    res = await fetch(boundariesUrl(level));
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error || `Boundaries unavailable (${res.status})`);
  }
  return res.json();
}

/**
 * Boundary GeoJSON for one level. One request per level is shared by every caller
 * (the map and the state-name index both need "state"); a failure is not cached.
 */
export function getBoundaries(level: BoundaryLevel): Promise<BoundaryCollection> {
  let p = boundaryCache.get(level);
  if (!p) {
    p = fetchBoundaries(level).catch((e) => {
      boundaryCache.delete(level);
      throw e;
    });
    boundaryCache.set(level, p);
  }
  return p;
}

let stateNames: Promise<Record<string, string>> | null = null;

/** Map of state place_id ("state:<code>") and bare code to state name. Cached. */
export function getStateNames(): Promise<Record<string, string>> {
  if (!stateNames) {
    stateNames = getBoundaries("state")
      .then((fc) => {
        const out: Record<string, string> = {};
        for (const f of fc.features ?? []) {
          const id: string = f.properties?.place_id;
          const name: string = f.properties?.name;
          if (!id || !name) continue;
          out[id] = name;
          out[id.replace(/^state:/, "")] = name;
        }
        return out;
      })
      .catch((e) => {
        stateNames = null;
        throw e;
      });
  }
  return stateNames;
}
