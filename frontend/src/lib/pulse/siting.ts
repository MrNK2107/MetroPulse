/**
 * Station siting: "what if a station opens here?"
 *
 * A site's catchment is every hexagon whose centre is inside the walk band
 * (captured at the walk rate) or the feeder band (captured at the lower feeder
 * rate). Boardings are average weekday trips in those hexagons times the
 * capture rate. Trips in hexagons already inside an existing hub's walk band
 * count as cannibalised, not new.
 *
 *   score = 60 x min(1, boardings / reference) + 40 x new share
 *
 * "Suggest sites" is a greedy search: score every hexagon by the new
 * boardings it would add, take the best, mark its catchment as covered, and
 * repeat, so each pick accounts for the ones before it (a pick covers its
 * whole feeder band, which spreads picks out into a network).
 */
import type { Point } from "./geo";
import { CityModel, HOURS_PER_WEEK } from "./model";

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

/** Existing hubs: the city's transport anchors, with a metro walk band. */
export function existingCoverage(model: CityModel): Set<number> {
  const covered = new Set<number>();
  for (const a of model.city.anchors) {
    if (a.type !== "transport") continue;
    const p = model.grid.project(a.lat, a.lng);
    for (const c of model.grid.within(p.x, p.y, MODES.metro.walkKm)) covered.add(c);
  }
  return covered;
}

export interface SiteResult {
  mode: ModeId;
  site: Point;
  walkCells: number[];
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

export function scoreSite(
  model: CityModel,
  site: Point,
  modeId: ModeId,
  covered: Set<number> = new Set()
): SiteResult {
  const mode = MODES[modeId];
  const { grid } = model;
  const walkCells = grid.within(site.x, site.y, mode.walkKm);
  const walkSet = new Set(walkCells);
  const feederCells = grid.within(site.x, site.y, mode.feederKm);

  let residents = 0;
  let jobs = 0;
  let boardings = 0;
  let fresh = 0;
  const hourly = new Array<number>(24).fill(0);
  for (const c of feederCells) {
    const rate = walkSet.has(c) ? mode.walkCapture : mode.feederCapture;
    const b = model.dailyTrips[c] * rate;
    boardings += b;
    if (!covered.has(c)) fresh += b;
    if (walkSet.has(c)) {
      residents += model.residents[c];
      jobs += model.jobs[c];
    }
    // weekday hourly shape (Mon-Fri average)
    for (let h = 0; h < 120; h++) hourly[h % 24] += (model.baselineMean[c * HOURS_PER_WEEK + h] * rate) / 5;
  }
  let peakHour = 0;
  for (let h = 1; h < 24; h++) if (hourly[h] > hourly[peakHour]) peakHour = h;
  const newShare = boardings > 0 ? fresh / boardings : 0;
  const volume = Math.min(1, boardings / mode.referenceBoardings);
  const score = Math.round(60 * volume + 40 * newShare);
  return {
    mode: modeId,
    site,
    walkCells,
    feederCells,
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
      ` + 40 x ${newShare.toFixed(2)} = ${score}`,
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
  start: Set<number> = existingCoverage(model)
): Suggestion[] {
  const mode = MODES[modeId];
  const { grid } = model;
  const covered = new Set(start);
  const picks: Suggestion[] = [];
  // Precompute catchments once.
  const walk = grid.cells.map((c) => grid.within(c.x, c.y, mode.walkKm));
  const feeder = grid.cells.map((c) => grid.within(c.x, c.y, mode.feederKm));
  for (let round = 0; round < k; round++) {
    let best = -1;
    let bestValue = -1;
    for (const c of grid.cells) {
      if (covered.has(c.index)) continue;
      const w = new Set(walk[c.index]);
      let v = 0;
      for (const f of feeder[c.index]) {
        if (covered.has(f)) continue;
        v += model.dailyTrips[f] * (w.has(f) ? mode.walkCapture : mode.feederCapture);
      }
      if (v > bestValue) {
        bestValue = v;
        best = c.index;
      }
    }
    if (best < 0) break;
    const cell = grid.cells[best];
    picks.push({ cell: best, result: scoreSite(model, cell, modeId, covered) });
    // the new station now serves its whole catchment
    for (const f of feeder[best]) covered.add(f);
  }
  return picks;
}

/** Share of residents living outside every existing hub's walk band. */
export function transitDesertShare(model: CityModel, covered: Set<number> = existingCoverage(model)): number {
  let total = 0;
  let inside = 0;
  for (let c = 0; c < model.residents.length; c++) {
    total += model.residents[c];
    if (covered.has(c)) inside += model.residents[c];
  }
  return total > 0 ? 1 - inside / total : 0;
}

/**
 * Share of residents within walking distance (the metro walk band) of an
 * existing hub or of any of the given sites. Each hexagon counts once.
 */
export function walkCoverage(model: CityModel, sites: SiteResult[] = []): number {
  const cells = existingCoverage(model);
  for (const s of sites) for (const c of s.walkCells) cells.add(c);
  let total = 0;
  let inside = 0;
  for (let c = 0; c < model.residents.length; c++) {
    total += model.residents[c];
    if (cells.has(c)) inside += model.residents[c];
  }
  return total > 0 ? inside / total : 0;
}
