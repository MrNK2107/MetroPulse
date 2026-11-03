/**
 * Line scenarios: a named, ordered set of stations of one mode.
 *
 * Stations are scored in order, each against coverage that already includes
 * the existing hubs and the earlier stations' feeder bands (the same rule the
 * greedy "suggest sites" search uses), so a line's boardings are net of its own
 * cannibalisation. Length is the sum of straight segments in the given order.
 *
 *   score = 50 x min(1, boardings / (n x reference)) + 30 x new share + 20 x spacing compliance
 *
 * The capital cost is a sketch from an editable table of order-of-magnitude
 * figures, labelled as assumptions wherever it is shown.
 */
import { getCity, hexDistanceKm, Point } from "./geo";
import type { CityModel } from "./model";
import { catchment, Coverage, existingCoverage, ModeId, MODES, scoreSite, SiteResult, Suggestion, suggestSites, walkCoverage } from "./siting";

export type Alignment = "elevated" | "underground" | "at-grade";

export interface CostTable {
  perKmCr: Record<Alignment, number>;
  perStationCr: Record<Alignment, number>;
}

export const DEFAULT_COSTS: CostTable = {
  perKmCr: { elevated: 250, underground: 600, "at-grade": 120 },
  perStationCr: { elevated: 60, underground: 250, "at-grade": 20 },
};

export const COST_SOURCE =
  "Order-of-magnitude figures from published Indian metro DPRs and MoHUA appraisals (2024, ₹ crore). Edit them to match your DPR.";

export const ALIGNMENTS: { id: Alignment; label: string }[] = [
  { id: "elevated", label: "Elevated" },
  { id: "underground", label: "Underground" },
  { id: "at-grade", label: "At grade" },
];

/** Acceptable distance between consecutive stations, km, per mode. */
export const SPACING_KM: Record<ModeId, [number, number]> = {
  metro: [0.8, 2.0],
  brt: [0.4, 1.2],
  feeder: [0.4, 1.2],
};

export interface ScenarioStation {
  lat: number;
  lng: number;
  name?: string;
}

export interface Scenario {
  id: string;
  cityId: string;
  name: string;
  mode: ModeId;
  alignment: Alignment;
  stations: ScenarioStation[];
  costs?: CostTable;
  notes?: string;
  /** Set when the line belongs to a team workspace (cloud); absent for personal lines. */
  workspaceId?: string;
  createdAt: string;
  updatedAt: string;
}

export type StationResult = SiteResult & {
  name: string;
  spacingKmToNext?: number;
  spacingWarning?: string;
};

export interface NetworkResult {
  stations: StationResult[];
  boardings: number;
  newBoardings: number;
  newShare: number;
  residents: number;
  jobs: number;
  coverageNow: number;
  coverageAfter: number;
  lengthKm: number;
  spacingCompliance: number;
  costCr: number;
  costPerBoardingLakh: number;
  score: number;
  formula: string;
  costFormula: string;
}

const inr = (n: number) => Math.round(n).toLocaleString("en-IN");

function serve(cover: Coverage, cells: number[], weights: number[]) {
  for (let k = 0; k < cells.length; k++) if (weights[k] > cover[cells[k]]) cover[cells[k]] = weights[k];
}

export function evaluateScenario(model: CityModel, scenario: Scenario): NetworkResult {
  const mode = MODES[scenario.mode];
  const costs = scenario.costs ?? DEFAULT_COSTS;
  const [minKm, maxKm] = SPACING_KM[scenario.mode];
  const covered = new Float32Array(existingCoverage(model));
  const points: Point[] = scenario.stations.map((s) => model.grid.project(s.lat, s.lng));

  const stations: StationResult[] = [];
  let boardings = 0;
  let newBoardings = 0;
  const walkUnion = new Float32Array(model.grid.cells.length);
  points.forEach((p, k) => {
    const r = scoreSite(model, p, scenario.mode, covered, model.calibration);
    boardings += r.dailyBoardings;
    newBoardings += r.newBoardings;
    const feeder = catchment(model.grid, p, mode.feederKm);
    serve(covered, feeder.cells, feeder.weights);
    const walk = catchment(model.grid, p, mode.walkKm);
    serve(walkUnion, walk.cells, walk.weights);
    const name = scenario.stations[k].name ?? `Station ${k + 1}`;
    stations.push({ ...r, name });
  });

  let lengthKm = 0;
  let inBand = 0;
  for (let k = 0; k + 1 < points.length; k++) {
    const d = hexDistanceKm(points[k], points[k + 1]);
    lengthKm += d;
    stations[k].spacingKmToNext = d;
    if (d < minKm) stations[k].spacingWarning = `${d.toFixed(1)} km to the next station, below the ${minKm} km band`;
    else if (d > maxKm) stations[k].spacingWarning = `${d.toFixed(1)} km to the next station, above the ${maxKm} km band`;
    else inBand++;
  }
  const pairs = Math.max(0, points.length - 1);
  const spacingCompliance = pairs === 0 ? 1 : inBand / pairs;

  let residents = 0;
  let jobs = 0;
  for (let c = 0; c < walkUnion.length; c++) {
    residents += model.residents[c] * walkUnion[c];
    jobs += model.jobs[c] * walkUnion[c];
  }

  const n = points.length;
  const newShare = boardings > 0 ? newBoardings / boardings : 0;
  const volume = n > 0 ? Math.min(1, boardings / (n * mode.referenceBoardings)) : 0;
  const score = Math.round(50 * volume + 30 * newShare + 20 * spacingCompliance);
  const costCr = lengthKm * costs.perKmCr[scenario.alignment] + n * costs.perStationCr[scenario.alignment];
  const costPerBoardingLakh = boardings > 0 ? (costCr * 100) / boardings : 0;

  return {
    stations,
    boardings,
    newBoardings,
    newShare,
    residents,
    jobs,
    coverageNow: walkCoverage(model),
    coverageAfter: walkCoverage(model, stations),
    lengthKm,
    spacingCompliance,
    costCr,
    costPerBoardingLakh,
    score,
    formula:
      `score = 50 x min(1, ${inr(boardings)} / (${n} x ${inr(mode.referenceBoardings)}))` +
      ` + 30 x ${newShare.toFixed(2)} + 20 x ${spacingCompliance.toFixed(2)} = ${score}`,
    costFormula:
      `cost = ${lengthKm.toFixed(1)} km x ₹${costs.perKmCr[scenario.alignment]} cr + ${n} x ₹${costs.perStationCr[scenario.alignment]} cr` +
      ` = ₹${inr(costCr)} cr; per daily boarding ₹${costPerBoardingLakh.toFixed(2)} lakh`,
  };
}

const ID_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789";

export function newScenarioId(): string {
  let out = "";
  for (let i = 0; i < 8; i++) out += ID_ALPHABET[Math.floor(Math.random() * ID_ALPHABET.length)];
  return out;
}

const MODE_CODE: Record<ModeId, string> = { metro: "m", brt: "b", feeder: "f" };
const ALIGN_CODE: Record<Alignment, string> = { elevated: "e", underground: "u", "at-grade": "g" };
const MAX_KM_FROM_CENTRE = 100;
export const MAX_STATIONS = 60;

/** `m.e.13.0418,80.2341;13.0418,80.2452`: mode, alignment, then lat,lng pairs to four decimals. */
export function encodeScenario(s: Scenario): string {
  const pts = s.stations.map((p) => `${p.lat.toFixed(4)},${p.lng.toFixed(4)}`).join(";");
  return `${MODE_CODE[s.mode]}.${ALIGN_CODE[s.alignment]}.${pts}`;
}

export function decodeScenario(text: string, cityId: string, centre?: [number, number]): Scenario | null {
  const m = /^([mbf])\.([eug])\.(.+)$/.exec(text ?? "");
  if (!m) return null;
  const mode = (Object.keys(MODE_CODE) as ModeId[]).find((k) => MODE_CODE[k] === m[1]);
  const alignment = (Object.keys(ALIGN_CODE) as Alignment[]).find((k) => ALIGN_CODE[k] === m[2]);
  if (!mode || !alignment) return null;
  const stations: ScenarioStation[] = [];
  for (const pair of m[3].split(";")) {
    const [a, b] = pair.split(",");
    const lat = Number(a);
    const lng = Number(b);
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return null;
    stations.push({ lat, lng });
  }
  if (stations.length === 0 || stations.length > MAX_STATIONS) return null;
  const c = centre ?? cityCentre(cityId);
  if (!c) return null;
  const kx = 111.32 * Math.cos((c[0] * Math.PI) / 180);
  for (const s of stations) {
    if (Math.hypot((s.lng - c[1]) * kx, (s.lat - c[0]) * 110.57) > MAX_KM_FROM_CENTRE) return null;
  }
  const now = new Date().toISOString();
  return { id: newScenarioId(), cityId, name: "Shared line", mode, alignment, stations, createdAt: now, updatedAt: now };
}

function cityCentre(cityId: string): [number, number] | null {
  const city = getCity(cityId);
  return city ? city.center : null;
}

/**
 * A corridor, not a hub network: the first station is the best single site; each next station
 * is the cell inside the spacing band of the previous one that adds the most new boardings,
 * with coverage updated as the line grows. Stops early if no cell in the band adds anything.
 */
export function suggestCorridor(model: CityModel, modeId: ModeId, k = 4): Scenario {
  const mode = MODES[modeId];
  const [minKm, maxKm] = SPACING_KM[modeId];
  const covered = new Float32Array(existingCoverage(model));
  const picks: Point[] = [];
  const first = suggestSites(model, modeId, 1, covered, model.calibration)[0];
  if (first) {
    const c = model.grid.cells[first.cell];
    picks.push({ x: c.x, y: c.y });
    const feeder = catchment(model.grid, c, mode.feederKm);
    serve(covered, feeder.cells, feeder.weights);
  }
  while (picks.length > 0 && picks.length < k) {
    const last = picks[picks.length - 1];
    let best: Point | null = null;
    let bestValue = 0;
    for (const idx of model.grid.within(last.x, last.y, maxKm)) {
      const c = model.grid.cells[idx];
      const d = hexDistanceKm(last, c);
      if (d < minKm || d > maxKm) continue;
      if (picks.some((p) => hexDistanceKm(p, c) < minKm)) continue;
      const v = scoreSite(model, c, modeId, covered, model.calibration).newBoardings;
      if (v > bestValue) {
        bestValue = v;
        best = { x: c.x, y: c.y };
      }
    }
    if (!best) break;
    picks.push(best);
    const feeder = catchment(model.grid, best, mode.feederKm);
    serve(covered, feeder.cells, feeder.weights);
  }
  const now = new Date().toISOString();
  return {
    id: newScenarioId(),
    cityId: model.city.id,
    name: `Suggested ${mode.label.split(" ")[0].toLowerCase()} corridor`,
    mode: modeId,
    alignment: "elevated",
    stations: picks.map((p) => {
      const { lat, lng } = model.grid.unproject(p);
      return { lat: Math.round(lat * 1e4) / 1e4, lng: Math.round(lng * 1e4) / 1e4 };
    }),
    createdAt: now,
    updatedAt: now,
  };
}

export function scenarioFromSuggestions(model: CityModel, modeId: ModeId, picks: Suggestion[]): Scenario {
  const now = new Date().toISOString();
  return {
    id: newScenarioId(),
    cityId: model.city.id,
    name: `Suggested ${MODES[modeId].label.split(" ")[0].toLowerCase()} line`,
    mode: modeId,
    alignment: "elevated",
    stations: picks.map((p) => {
      const { lat, lng } = model.grid.unproject(model.grid.cells[p.cell]);
      return { lat, lng };
    }),
    createdAt: now,
    updatedAt: now,
  };
}
