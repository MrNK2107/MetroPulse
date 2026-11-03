/**
 * Station siting: "what if a station opens here?"
 *
 * A site's catchment is two circles: the walk band (captured at the walk rate)
 * and the feeder band (captured at the lower feeder rate). Each hexagon counts
 * by the share of its area inside a circle, so a pin's score does not jump
 * depending on where inside a hexagon it lands. Boardings are average weekday
 * trips times the capture rate. Trips in hexagons already served by an
 * existing hub's walk band count as cannibalised, not new.
 *
 *   score = 60 x min(1, boardings / reference) + 40 x new share
 *
 * "Suggest sites" is a greedy search: score every hexagon by the new
 * boardings it would add, take the best, mark its catchment as served, and
 * repeat, so each pick accounts for the ones before it (a pick serves its
 * whole feeder band, which spreads picks out into a network).
 */
import type { HexGrid, Point } from "./geo";
import type { CityModel } from "./model";
import type { Calibration } from "./calibrate";
import { HOURS_PER_WEEK } from "./time";

export type ModeId = "metro" | "brt" | "feeder";

export interface Mode {
  id: ModeId;
  label: string;
  walkKm: number;
  feederKm: number;
  walkCapture: number;
  feederCapture: number;
  referenceBoardings: number;
}

export const MODES: Record<ModeId, Mode> = {
  metro: {
    id: "metro",
    label: "Metro station",
    walkKm: 0.8,
    feederKm: 2.5,
    walkCapture: 0.04,
    feederCapture: 0.01,
    referenceBoardings: 50000,
  },
  brt: {
    id: "brt",
    label: "BRT stop",
    walkKm: 0.5,
    feederKm: 1.5,
    walkCapture: 0.03,
    feederCapture: 0.008,
    referenceBoardings: 15000,
  },
  feeder: {
    id: "feeder",
    label: "Feeder bus stop",
    walkKm: 0.4,
    feederKm: 0.8,
    walkCapture: 0.015,
    feederCapture: 0.004,
    referenceBoardings: 3000,
  },
};

/** Sample points spread evenly over one hexagon, relative to its centre. */
const samplesCache = new Map<number, Point[]>();
function hexSamples(edgeKm: number): Point[] {
  const hit = samplesCache.get(edgeKm);
  if (hit) return hit;
  const step = edgeKm / 3;
  const half = (Math.sqrt(3) / 2) * edgeKm;
  const out: Point[] = [];
  // a triangular lattice clipped to the pointy-top hexagon
  for (let j = -6; j <= 6; j++) {
    const y = (j * step * Math.sqrt(3)) / 2;
    for (let i = -6; i <= 6; i++) {
      const x = (i + (j & 1 ? 0.5 : 0)) * step;
      if (Math.abs(x) <= half + 1e-9 && Math.abs(y) <= edgeKm - Math.abs(x) / Math.sqrt(3) + 1e-9) out.push({ x, y });
    }
  }
  samplesCache.set(edgeKm, out);
  return out;
}

export interface Catchment {
  cells: number[];
  /** Share (0-1] of each cell's area inside the circle, aligned with cells. */
  weights: number[];
}

/** Hexagons overlapping a circle, each weighted by the share of its area inside it. */
export function catchment(grid: HexGrid, centre: Point, radiusKm: number): Catchment {
  const samples = hexSamples(grid.edgeKm);
  const r2 = radiusKm * radiusKm;
  const cells: number[] = [];
  const weights: number[] = [];
  for (const c of grid.within(centre.x, centre.y, radiusKm + grid.edgeKm)) {
    const cx = grid.cells[c].x - centre.x;
    const cy = grid.cells[c].y - centre.y;
    let inside = 0;
    for (const s of samples) {
      const dx = cx + s.x;
      const dy = cy + s.y;
      if (dx * dx + dy * dy <= r2) inside++;
    }
    if (inside > 0) {
      cells.push(c);
      weights.push(inside / samples.length);
    }
  }
  return { cells, weights };
}

/** Per hexagon, the share (0-1) already within walking distance of something. */
export type Coverage = Float32Array;

function serve(cover: Coverage, c: Catchment) {
  for (let k = 0; k < c.cells.length; k++) if (c.weights[k] > cover[c.cells[k]]) cover[c.cells[k]] = c.weights[k];
}

/** Existing hubs (the user's stations, or the city's transport anchors), each with its own mode's walk band. */
export function existingCoverage(model: CityModel): Coverage {
  const cover = new Float32Array(model.grid.cells.length);
  for (const h of model.hubs) {
    serve(cover, catchment(model.grid, model.grid.project(h.lat, h.lng), MODES[h.mode].walkKm));
  }
  return cover;
}

/** Hexagons drawn as part of a band: at least a quarter of their area inside it. */
const DRAW_SHARE = 0.25;

export interface SiteResult {
  mode: ModeId;
  site: Point;
  /** Hexagons to draw as the walk band (at least 25% of their area inside it). */
  walkCells: number[];
  /** Hexagons to draw as the feeder band. */
  feederCells: number[];
  residents: number;
  jobs: number;
  dailyBoardings: number;
  newBoardings: number;
  newShare: number;
  peakHour: number;
  hourly: number[];
  score: number;
  formula: string;
}

/** Capture rate per feeder-band hexagon: walk share at the walk rate, the rest of the feeder share at the feeder rate. */
function captureRates(walk: Catchment, feeder: Catchment, mode: Mode): number[] {
  const w = new Map<number, number>();
  walk.cells.forEach((c, k) => w.set(c, walk.weights[k]));
  // the walk circle sits inside the feeder circle, so feeder-only area = feeder share - walk share
  return feeder.cells.map((c, k) => {
    const ww = w.get(c) ?? 0;
    return ww * mode.walkCapture + Math.max(0, feeder.weights[k] - ww) * mode.feederCapture;
  });
}

export function scoreSite(
  model: CityModel,
  site: Point,
  modeId: ModeId,
  covered?: Coverage,
  calibration?: Calibration
): SiteResult {
  const mode = MODES[modeId];
  const factor = calibration?.factor[modeId] ?? 1;
  const calibrated = calibration !== undefined && calibration.stations[modeId] >= 3;
  const walk = catchment(model.grid, site, mode.walkKm);
  const feeder = catchment(model.grid, site, mode.feederKm);
  const rates = captureRates(walk, feeder, mode);

  let residents = 0;
  let jobs = 0;
  walk.cells.forEach((c, k) => {
    residents += model.residents[c] * walk.weights[k];
    jobs += model.jobs[c] * walk.weights[k];
  });

  let boardings = 0;
  let fresh = 0;
  const hourly = new Array<number>(24).fill(0);
  feeder.cells.forEach((c, k) => {
    const rate = rates[k];
    const b = model.dailyTrips[c] * rate * factor;
    boardings += b;
    fresh += b * (1 - (covered ? covered[c] : 0));
    // weekday hourly shape (Mon-Fri average)
    for (let h = 0; h < 120; h++) hourly[h % 24] += (model.baselineMean[c * HOURS_PER_WEEK + h] * rate * factor) / 5;
  });
  let peakHour = 0;
  for (let h = 1; h < 24; h++) if (hourly[h] > hourly[peakHour]) peakHour = h;
  const newShare = boardings > 0 ? fresh / boardings : 0;
  const volume = Math.min(1, boardings / mode.referenceBoardings);
  const score = Math.round(60 * volume + 40 * newShare);
  return {
    mode: modeId,
    site,
    walkCells: walk.cells.filter((_, k) => walk.weights[k] >= DRAW_SHARE),
    feederCells: feeder.cells.filter((_, k) => feeder.weights[k] >= DRAW_SHARE),
    residents,
    jobs,
    dailyBoardings: boardings,
    newBoardings: fresh,
    newShare,
    peakHour,
    hourly,
    score,
    formula:
      `score = 60 x min(1, ${Math.round(boardings).toLocaleString("en-IN")} / ${mode.referenceBoardings.toLocaleString("en-IN")})` +
      ` + 40 x ${newShare.toFixed(2)} = ${score}` +
      (calibrated
        ? `; boardings × ${factor.toFixed(2)} (calibrated on ${calibration.stations[modeId]} stations, IQR ±${Math.round(
            calibration.iqr[modeId] * 100
          )}%)`
        : ""),
  };
}

export interface Suggestion {
  cell: number;
  result: SiteResult;
}

export function suggestSites(
  model: CityModel,
  modeId: ModeId,
  k = 3,
  start: Coverage = existingCoverage(model),
  calibration?: Calibration
): Suggestion[] {
  const mode = MODES[modeId];
  const { grid } = model;
  const covered = new Float32Array(start);
  const picks: Suggestion[] = [];
  // Precompute every hexagon's catchment and capture rates once.
  const bands = grid.cells.map((c) => {
    const feeder = catchment(grid, c, mode.feederKm);
    return { feeder, rates: captureRates(catchment(grid, c, mode.walkKm), feeder, mode) };
  });
  for (let round = 0; round < k; round++) {
    let best = -1;
    let bestValue = -1;
    for (const c of grid.cells) {
      if (covered[c.index] >= 0.5) continue;
      const { feeder, rates } = bands[c.index];
      let v = 0;
      for (let j = 0; j < feeder.cells.length; j++) {
        const f = feeder.cells[j];
        v += model.dailyTrips[f] * rates[j] * (1 - covered[f]);
      }
      if (v > bestValue) {
        bestValue = v;
        best = c.index;
      }
    }
    if (best < 0) break;
    picks.push({ cell: best, result: scoreSite(model, grid.cells[best], modeId, covered, calibration) });
    // the new station now serves its whole catchment
    serve(covered, bands[best].feeder);
  }
  return picks;
}

function residentShare(model: CityModel, cover: Coverage): number {
  let total = 0;
  let inside = 0;
  for (let c = 0; c < model.residents.length; c++) {
    total += model.residents[c];
    inside += model.residents[c] * cover[c];
  }
  return total > 0 ? inside / total : 0;
}

/** Share of residents living outside every existing hub's walk band. */
export function transitDesertShare(model: CityModel, covered: Coverage = existingCoverage(model)): number {
  return 1 - residentShare(model, covered);
}

/**
 * Share of residents within walking distance (the metro walk band) of an
 * existing hub or of any of the given sites. Overlaps count once.
 */
export function walkCoverage(model: CityModel, sites: SiteResult[] = []): number {
  const cover = existingCoverage(model);
  for (const s of sites) serve(cover, catchment(model.grid, s.site, MODES.metro.walkKm));
  return residentShare(model, cover);
}
