/**
 * Calibration against observed station counts.
 *
 * For every count row that matches a loaded hub, the model's own boardings at
 * that hub (scoreSite, no cannibalisation) are compared with the observed
 * daily boardings. The factor per mode is the median observed/modelled ratio
 * over that mode's matched stations, used only when at least 3 stations
 * matched. The spread is the inter-quartile range of the ratios divided by the
 * median, shown as a ± band. Calibration scales the model's outputs; it does
 * not rebuild the demand field.
 */
import { normaliseStationName } from "./import/counts";
import type { CityModel } from "./model";
import { ModeId, scoreSite } from "./siting";

export interface Calibration {
  factor: Record<ModeId, number>;
  stations: Record<ModeId, number>;
  iqr: Record<ModeId, number>;
  matched: { station: string; mode: ModeId; observed: number; modelled: number }[];
  unmatched: string[];
}

export const MIN_STATIONS = 3;

export const UNCALIBRATED: Calibration = Object.freeze({
  factor: { metro: 1, brt: 1, feeder: 1 },
  stations: { metro: 0, brt: 0, feeder: 0 },
  iqr: { metro: 0, brt: 0, feeder: 0 },
  matched: [],
  unmatched: [],
}) as Calibration;

function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return 0;
  const pos = (sorted.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

export function calibrate(model: CityModel, counts: { station: string; dailyBoardings: number }[]): Calibration {
  const byKey = new Map<string, number>();
  model.hubs.forEach((h, k) => {
    const key = normaliseStationName(h.name);
    if (!byKey.has(key)) byKey.set(key, k);
  });
  const matched: Calibration["matched"] = [];
  const unmatched: string[] = [];
  const modelledCache = new Map<number, number>();
  const seen = new Set<number>();
  for (const row of counts) {
    const k = byKey.get(normaliseStationName(row.station));
    if (k === undefined) {
      unmatched.push(row.station);
      continue;
    }
    if (seen.has(k)) continue; // two rows naming the same station: the first one counts
    seen.add(k);
    const hub = model.hubs[k];
    let modelled = modelledCache.get(k);
    if (modelled === undefined) {
      modelled = scoreSite(model, model.grid.project(hub.lat, hub.lng), hub.mode).dailyBoardings;
      modelledCache.set(k, modelled);
    }
    matched.push({ station: hub.name, mode: hub.mode, observed: row.dailyBoardings, modelled });
  }
  const factor = { ...UNCALIBRATED.factor };
  const stations = { ...UNCALIBRATED.stations };
  const iqr = { ...UNCALIBRATED.iqr };
  for (const mode of Object.keys(factor) as ModeId[]) {
    const ratios = matched
      .filter((m) => m.mode === mode && m.modelled > 0)
      .map((m) => m.observed / m.modelled)
      .sort((a, b) => a - b);
    stations[mode] = ratios.length;
    if (ratios.length < MIN_STATIONS) continue;
    const median = quantile(ratios, 0.5);
    if (!(median > 0)) continue; // all-zero counts cannot calibrate a mode
    factor[mode] = median;
    iqr[mode] = median > 0 ? (quantile(ratios, 0.75) - quantile(ratios, 0.25)) / median : 0;
  }
  return { factor, stations, iqr, matched, unmatched };
}
