/**
 * The MetroPulse sample city model.
 *
 * A deterministic, seeded, synthetic demand field. Each hexagon gets residents
 * and jobs from the city's real anchor points (CBDs, job hubs, transport hubs,
 * residential centres) and its published population. Hourly demand comes from
 * commute, leisure and hub profiles for weekdays and weekends. Four baseline
 * weeks carry ordinary noise; the current week also carries scripted incidents
 * so the detector has something to find.
 *
 * The algorithms downstream are real. These numbers are illustrative.
 */
import { buildHexGrid, City, HexGrid, Point, Anchor } from "./geo";
import type { Station } from "./import/types";
import { CityData, cityDataKey } from "./userdata";

import { HOURS_PER_WEEK } from "./time";
import { calibrate, Calibration, UNCALIBRATED } from "./calibrate";

export { HOURS_PER_WEEK, DAYS, dayHourLabel, hourLabel } from "./time";

export interface ScriptedIncident {
  kind: "surge" | "drop";
  story: string;
  anchor: string;
  startHour: number;
  endHour: number;
  peakHour: number;
  radiusKm: number;
  factor: number;
}

export interface CityModel {
  city: City;
  grid: HexGrid;
  residents: Float32Array;
  jobs: Float32Array;
  /** Average weekday trips touching each cell. */
  dailyTrips: Float32Array;
  /** 4 trailing weeks, each cells x 168, index cell * 168 + hour. */
  baselineWeeks: Float32Array[];
  baselineMean: Float32Array;
  thisWeek: Float32Array;
  scripted: ScriptedIncident[];
  /** Existing stations: the user's, or the city's transport anchors as metro stations. */
  hubs: Station[];
  /** The user's own data this model was built from, if any. */
  data: CityData | null;
  /** Boardings scale factors from observed counts; UNCALIBRATED without counts. */
  calibration: Calibration;
  cityHourly(week: Float32Array): number[];
  rankCellsByDailyTrips(): number[];
  nearestAnchor(p: Point): { anchor: Anchor; km: number };
}

export function seedFrom(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function normal(rand: () => number): number {
  const u = Math.max(rand(), 1e-12);
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand());
}

const g = (h: number, mu: number, sd: number) => Math.exp(-0.5 * ((h - mu) / sd) ** 2);
function profile(fn: (h: number) => number): number[] {
  const v = Array.from({ length: 24 }, (_, h) => fn(h));
  const s = v.reduce((a, b) => a + b, 0);
  return v.map((x) => x / s);
}

const P = {
  resWeekday: profile((h) => 0.45 * g(h, 8.5, 1.2) + 0.4 * g(h, 19, 1.5) + 0.15 * g(h, 13, 3) + 0.01),
  resWeekend: profile((h) => 0.3 * g(h, 10.5, 2) + 0.4 * g(h, 19.5, 2) + 0.3 * g(h, 14, 3) + 0.01),
  jobWeekday: profile((h) => 0.45 * g(h, 9.5, 1) + 0.45 * g(h, 18.5, 1.3) + 0.1 * g(h, 13.5, 1.2) + 0.005),
  jobWeekend: profile((h) => 0.5 * g(h, 10.5, 1.5) + 0.5 * g(h, 17.5, 1.8) + 0.005),
  leisure: profile((h) => 0.3 * g(h, 13, 2.5) + 0.7 * g(h, 19.5, 2) + 0.005),
  hub: profile((h) => 0.4 * g(h, 8.5, 1.3) + 0.4 * g(h, 18.5, 1.6) + 0.2 * g(h, 13, 4) + 0.01),
};

const JOB_TYPES = new Set([
  "cbd",
  "commercial",
  "industrial",
  "tech_park",
  "sez",
  "technology",
  "biotech_park",
  "port",
  "trade",
  "economic",
  "it",
]);
const LEISURE_TYPES = new Set(["cbd", "commercial", "tourism", "heritage", "trade"]);
const RESIDENTIAL_TYPES = new Set(["residential", "housing"]);

function gauss(d: number, sd: number) {
  return Math.exp(-0.5 * (d / sd) ** 2);
}

function normalise(arr: Float32Array, total: number) {
  let s = 0;
  for (let i = 0; i < arr.length; i++) s += arr[i];
  s = s || 1;
  for (let i = 0; i < arr.length; i++) arr[i] = (arr[i] / s) * total;
}

function pickAnchor(anchors: Anchor[], types: string[], fallback: number): Anchor {
  for (const t of types) {
    const a = anchors.find((x) => x.type === t);
    if (a) return a;
  }
  return anchors[Math.min(fallback, anchors.length - 1)];
}

const cache = new Map<string, CityModel>();
/** Each model holds several Float32Arrays of cells x 168; keep only the most recent few. */
const CACHE_LIMIT = 8;

export function modelCacheSize(): number {
  return cache.size;
}

/** Memoised: the model is deterministic per city. */
export function getCityModel(city: City, data?: CityData | null): CityModel {
  const key = `${city.id}:${cityDataKey(data)}`;
  let m = cache.get(key);
  if (!m) {
    m = buildCityModel(city, data);
    cache.set(key, m);
    while (cache.size > CACHE_LIMIT) cache.delete(cache.keys().next().value as string);
  }
  return m;
}

/** The city's configured transport anchors, as metro stations. */
export function anchorHubs(city: City): Station[] {
  return city.anchors.filter((a) => a.type === "transport").map((a) => ({ name: a.name, lat: a.lat, lng: a.lng, mode: "metro" }));
}

/** Default spread of a survey zone around its centroid, km (about one TAZ in a dense Indian city). */
export const ZONE_RADIUS_KM = 1.2;

export function buildCityModel(baseCity: City, data?: CityData | null): CityModel {
  const zones = data?.zones?.rows ?? null;
  const zonePopulation = zones ? zones.reduce((a, z) => a + z.residents, 0) : 0;
  const city: City = {
    ...baseCity,
    ...(data?.boundary ? { boundary: data.boundary.ring } : {}),
    ...(zones && zonePopulation > 0 ? { population: Math.round(zonePopulation) } : {}),
  };
  const grid = buildHexGrid(city);
  const n = grid.cells.length;
  const rand = mulberry32(seedFrom(city.id));
  const hubs: Station[] = data?.hubs ? data.hubs.stations : anchorHubs(city);
  const hubPoints = hubs.map((h) => grid.project(h.lat, h.lng));
  // Place names come from the configured anchors; the user's stations replace the transport anchors.
  const named: Anchor[] = data?.hubs
    ? [...city.anchors.filter((a) => a.type !== "transport"), ...hubs.map((h) => ({ name: h.name, type: "transport", lat: h.lat, lng: h.lng, weight: 0 }))]
    : city.anchors;
  const anchors = named.map((a) => ({ a, p: grid.project(a.lat, a.lng) }));
  const extent = Math.sqrt(n * grid.cellAreaKm2);

  const residents = new Float32Array(n);
  const jobs = new Float32Array(n);
  const leisure = new Float32Array(n);
  const hub = new Float32Array(n);
  for (const c of grid.cells) {
    const d0 = Math.hypot(c.x, c.y);
    let res = 0.6 * Math.exp(-d0 / (extent / 3));
    let job = 0.08 * Math.exp(-d0 / (extent / 4));
    let lei = 0;
    let hb = 0;
    for (const { a, p } of anchors) {
      if (a.type === "transport") continue; // hubs are handled below
      const d = Math.hypot(c.x - p.x, c.y - p.y);
      if (RESIDENTIAL_TYPES.has(a.type)) res += 1.5 * a.weight * gauss(d, 2.5);
      if (a.type === "cbd") res += 0.4 * a.weight * gauss(d, 2);
      if (JOB_TYPES.has(a.type)) job += a.weight * gauss(d, 1.6);
      if (LEISURE_TYPES.has(a.type)) lei += a.weight * gauss(d, 1.5);
    }
    for (const p of hubPoints) hb += gauss(Math.hypot(c.x - p.x, c.y - p.y), 0.9);
    residents[c.index] = res * (0.7 + 0.6 * rand());
    jobs[c.index] = job * (0.7 + 0.6 * rand());
    leisure[c.index] = lei + 0.002;
    hub[c.index] = hb;
  }
  if (zones) {
    // The user's zones replace the synthetic residents and jobs: each zone is spread over the
    // hexagons within three radii of its centroid with Gaussian weights, keeping its totals.
    residents.fill(0);
    jobs.fill(0);
    for (const z of zones) {
      const p = grid.project(z.lat, z.lng);
      const sd = z.radiusKm && z.radiusKm > 0 ? z.radiusKm : ZONE_RADIUS_KM;
      const near = grid.within(p.x, p.y, 3 * sd);
      let sum = 0;
      const w = near.map((c) => {
        const v = gauss(Math.hypot(grid.cells[c].x - p.x, grid.cells[c].y - p.y), sd);
        sum += v;
        return v;
      });
      if (sum <= 0) continue;
      near.forEach((c, k) => {
        residents[c] += (z.residents * w[k]) / sum;
        jobs[c] += (z.jobs * w[k]) / sum;
      });
    }
  } else {
    normalise(residents, city.population);
    normalise(jobs, city.population * 0.4);
  }
  normalise(leisure, city.population * 0.25);
  normalise(hub, city.population * 0.15);

  const baselineMean = new Float32Array(n * HOURS_PER_WEEK);
  for (let c = 0; c < n; c++) {
    for (let h = 0; h < HOURS_PER_WEEK; h++) {
      const day = Math.floor(h / 24);
      const hr = h % 24;
      const weekend = day >= 5;
      baselineMean[c * HOURS_PER_WEEK + h] =
        residents[c] * 1.4 * (weekend ? 0.7 * P.resWeekend[hr] : P.resWeekday[hr]) +
        jobs[c] * 2 * (weekend ? 0.35 * P.jobWeekend[hr] : P.jobWeekday[hr]) +
        leisure[c] * (weekend ? 1.6 : 1) * P.leisure[hr] +
        hub[c] * (weekend ? 0.6 : 1) * P.hub[hr];
    }
  }

  const noisyWeek = (r: () => number) => {
    const w = new Float32Array(n * HOURS_PER_WEEK);
    const global = 1 + 0.02 * normal(r);
    for (let i = 0; i < w.length; i++) w[i] = Math.max(0, baselineMean[i] * global * (1 + 0.06 * normal(r)));
    return w;
  };
  const baselineWeeks = [0, 1, 2, 3].map((k) => noisyWeek(mulberry32(seedFrom(`${city.id}:week:${k}`))));
  const thisWeek = noisyWeek(mulberry32(seedFrom(`${city.id}:week:now`)));

  // Scripted incidents in the current week, so the detector has something to find.
  // Some configured anchors sit outside the procedural boundary; only use ones
  // with enough hexagons around them to be visible.
  const A = city.anchors.filter((a) => {
    const p = grid.project(a.lat, a.lng);
    return grid.within(p.x, p.y, 1.0).length >= 3;
  });
  if (A.length === 0) A.push(...city.anchors);
  const eventAt = pickAnchor(A, ["cbd", "commercial", "tourism", "transport"], 0);
  const homeAt = pickAnchor(A, ["residential", "housing"], 1);
  const workAt = pickAnchor(A, ["industrial", "tech_park", "sez", "technology"], 2);
  const scripted: ScriptedIncident[] = [
    {
      kind: "surge",
      story: "Evening crowd release after a large event",
      anchor: eventAt.name,
      startHour: 4 * 24 + 18,
      endHour: 4 * 24 + 22,
      peakHour: 4 * 24 + 20,
      radiusKm: 1.3,
      factor: 2.6,
    },
    {
      kind: "drop",
      story: "Morning departures cut by waterlogging on the approach roads",
      anchor: homeAt.name,
      startHour: 1 * 24 + 7,
      endHour: 1 * 24 + 10,
      peakHour: 1 * 24 + 8,
      radiusKm: 1.5,
      factor: 0.35,
    },
    {
      kind: "surge",
      story: "Mid-shift intake at a large employer",
      anchor: workAt.name,
      startHour: 2 * 24 + 13,
      endHour: 2 * 24 + 15,
      peakHour: 2 * 24 + 14,
      radiusKm: 1.0,
      factor: 2.0,
    },
  ];
  for (const s of scripted) {
    const a = A.find((x) => x.name === s.anchor)!;
    const p = grid.project(a.lat, a.lng);
    while (grid.within(p.x, p.y, s.radiusKm).length < 6 && s.radiusKm < 2.5) s.radiusKm += 0.25;
    const span = Math.max(1, (s.endHour - s.startHour) / 2);
    for (const c of grid.within(p.x, p.y, s.radiusKm)) {
      const fall = 1 - 0.4 * (Math.hypot(grid.cells[c].x - p.x, grid.cells[c].y - p.y) / s.radiusKm);
      for (let h = s.startHour; h <= s.endHour; h++) {
        const t = 1 - 0.5 * (Math.abs(h - s.peakHour) / span);
        const f = 1 + (s.factor - 1) * fall * Math.max(0.5, t);
        thisWeek[c * HOURS_PER_WEEK + h] *= f;
      }
    }
  }

  const dailyTrips = new Float32Array(n);
  for (let c = 0; c < n; c++) {
    let s = 0;
    for (let h = 0; h < 120; h++) s += baselineMean[c * HOURS_PER_WEEK + h];
    dailyTrips[c] = s / 5;
  }

  let ranked: number[] | null = null;
  const model: CityModel = {
    city,
    grid,
    residents,
    jobs,
    dailyTrips,
    baselineWeeks,
    baselineMean,
    thisWeek,
    scripted,
    hubs,
    data: data ?? null,
    calibration: UNCALIBRATED,
    cityHourly(week) {
      const out = new Array<number>(HOURS_PER_WEEK).fill(0);
      for (let c = 0; c < n; c++)
        for (let h = 0; h < HOURS_PER_WEEK; h++) out[h] += week[c * HOURS_PER_WEEK + h];
      return out;
    },
    rankCellsByDailyTrips() {
      if (!ranked) ranked = Array.from({ length: n }, (_, i) => i).sort((a, b) => dailyTrips[b] - dailyTrips[a]);
      return ranked;
    },
    nearestAnchor(p) {
      let best = anchors[0];
      let bd = Infinity;
      for (const x of anchors) {
        const d = Math.hypot(p.x - x.p.x, p.y - x.p.y);
        if (d < bd) {
          bd = d;
          best = x;
        }
      }
      return { anchor: best.a, km: bd };
    },
  };
  if (data?.counts && data.hubs) model.calibration = calibrate(model, data.counts.rows);
  return model;
}

const scaleCache = new WeakMap<CityModel, number>();

/** Colour-scale ceiling: half the busiest baseline hex-hour (the map uses a sqrt ramp). */
export function demandScaleMax(model: CityModel): number {
  const hit = scaleCache.get(model);
  if (hit) return hit;
  let max = 0;
  const arr = model.baselineMean;
  for (let i = 0; i < arr.length; i++) if (arr[i] > max) max = arr[i];
  const v = max * 0.5 || 1;
  scaleCache.set(model, v);
  return v;
}
