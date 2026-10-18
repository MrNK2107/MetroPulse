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

let stateNames: Promise<Record<string, string>> | null = null;

/** Map of state place_id ("state:<code>") and bare code to state name. Cached. */
export function getStateNames(): Promise<Record<string, string>> {
  if (!stateNames) {
    stateNames = fetch(boundariesUrl("state"))
      .then((r) => {
        if (!r.ok) throw new Error(`Request failed (${r.status})`);
        return r.json();
      })
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
