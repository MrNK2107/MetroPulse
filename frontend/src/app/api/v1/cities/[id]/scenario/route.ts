import { Alignment, CostTable, DEFAULT_COSTS, evaluateScenario, Scenario } from "@/lib/pulse/scenario";
import { MODES, ModeId } from "@/lib/pulse/siting";
import { fail, nearCity, ok, preflight, withCity } from "@/lib/api/envelope";

const ALIGNMENTS = new Set<Alignment>(["elevated", "underground", "at-grade"]);

/** A cost table is two records over the three alignments, every value a finite number >= 0. */
function validCosts(c: unknown): c is CostTable {
  if (!c || typeof c !== "object") return false;
  const t = c as Record<string, unknown>;
  for (const key of ["perKmCr", "perStationCr"]) {
    const rec = t[key];
    if (!rec || typeof rec !== "object") return false;
    for (const a of ALIGNMENTS) {
      const v = (rec as Record<string, unknown>)[a];
      if (typeof v !== "number" || !Number.isFinite(v) || v < 0) return false;
    }
  }
  return true;
}

export async function POST(req: Request, { params }: { params: { id: string } }) {
  let body: Partial<Scenario>;
  try {
    body = (await req.json()) as Partial<Scenario>;
  } catch {
    return fail(400, "bad_request", "The body must be JSON");
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) return fail(400, "bad_request", "The body must be a JSON object");
  if (body.costs !== undefined && !validCosts(body.costs)) {
    return fail(400, "bad_request", "costs must be { perKmCr, perStationCr }, each with finite non-negative elevated, underground and at-grade values");
  }
  const mode = (body.mode ?? "metro") as ModeId;
  const alignment = (body.alignment ?? "elevated") as Alignment;
  if (!Object.hasOwn(MODES, mode)) return fail(400, "bad_request", `mode must be one of ${Object.keys(MODES).join(", ")}`);
  if (!ALIGNMENTS.has(alignment)) return fail(400, "bad_request", "alignment must be elevated, underground or at-grade");
  const stations = Array.isArray(body.stations) ? body.stations : [];
  if (stations.length === 0 || stations.length > 60) return fail(400, "bad_request", "stations must list 1 to 60 {lat, lng} points");
  for (const s of stations) {
    if (!s || !Number.isFinite(s.lat) || !Number.isFinite(s.lng)) return fail(400, "bad_request", "every station needs numeric lat and lng");
  }
  return withCity(params.id, (model) => {
    if (stations.some((s) => !nearCity(model, s.lat, s.lng))) return fail(400, "bad_request", "A station is more than 100 km from the city centre");
    const now = new Date().toISOString();
    const scenario: Scenario = {
      id: "api",
      cityId: model.city.id,
      name: typeof body.name === "string" ? body.name.slice(0, 80) : "API line",
      mode,
      alignment,
      stations: stations.map((s) => ({ lat: s.lat, lng: s.lng, ...(typeof s.name === "string" ? { name: s.name.slice(0, 80) } : {}) })),
      costs: body.costs ?? DEFAULT_COSTS,
      createdAt: now,
      updatedAt: now,
    };
    const r = evaluateScenario(model, scenario);
    return ok({ ...r, stations: r.stations.map(({ walkCells: _w, feederCells: _f, site: _s, ...rest }) => rest) }, { costs: scenario.costs });
  });
}

export const OPTIONS = preflight;
