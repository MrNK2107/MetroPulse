/**
 * Observed station counts. Three shapes are accepted and all reduce to one
 * daily boardings figure per station:
 *   station, daily_boardings
 *   station, date, boardings      (mean over the dates)
 *   station, hour, boardings      (sum over the hours of one day)
 */
import { findColumn, parseCsv, toNumber } from "./csv";
import { fail, ok, ParseResult } from "./types";

export interface CountRow {
  station: string;
  dailyBoardings: number;
}

const STATION = ["station", "stop", "stop_name", "name", "station_name"];
const DAILY = ["daily_boardings", "daily", "avg_daily_boardings", "boardings_per_day"];
const VALUE = ["boardings", "riders", "entries", "taps", "ridership", "count"];

/** "M.G. Road Metro Station" -> "mg road": the key used to match counts to hubs. */
export function normaliseStationName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[.'’]/g, "")
    .replace(/\b(metro|station|stn|halt|stop)\b/g, " ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

export interface CountsDetail {
  rows: CountRow[];
  /** When counts come by hour: the share of the day in each of the 24 hours, summed across stations. */
  hourly?: number[];
}

export function parseCountsCsv(text: string): ParseResult<CountRow[]> {
  const r = parseCountsDetailed(text);
  return r.ok ? ok(r.value.rows, r.report) : r;
}

export function parseCountsDetailed(text: string): ParseResult<CountsDetail> {
  const { header, rows } = parseCsv(text);
  const iStation = findColumn(header, STATION);
  if (iStation < 0) return fail("No station column (expected one of: station, stop_name, name)");
  const iDaily = findColumn(header, DAILY);
  const iValue = iDaily >= 0 ? iDaily : findColumn(header, VALUE);
  if (iValue < 0) return fail("No boardings column (expected one of: daily_boardings, boardings, riders, entries, taps)");
  const iDate = findColumn(header, ["date", "day"]);
  const iHour = findColumn(header, ["hour", "hr"]);
  const shape: "daily" | "by-date" | "by-hour" = iDaily >= 0 ? "daily" : iDate >= 0 ? "by-date" : iHour >= 0 ? "by-hour" : "daily";

  const sum = new Map<string, number>();
  const dates = new Map<string, Set<string>>();
  const order: string[] = [];
  const byHour = new Array<number>(24).fill(0);
  let skipped = 0;
  for (const r of rows) {
    const station = (r[iStation] ?? "").trim();
    const v = toNumber(r[iValue]);
    if (!station || v === null || v < 0) {
      skipped++;
      continue;
    }
    if (shape === "by-hour") {
      const hr = toNumber(r[iHour]);
      if (hr === null || hr < 0 || hr > 23) {
        skipped++;
        continue;
      }
      byHour[Math.floor(hr)] += v;
    }
    if (!sum.has(station)) {
      sum.set(station, 0);
      dates.set(station, new Set());
      order.push(station);
    }
    sum.set(station, sum.get(station)! + v);
    if (shape === "by-date") dates.get(station)!.add((r[iDate] ?? "").trim());
  }
  if (order.length === 0) return fail("No usable rows: each row needs a station name and a numeric boardings value");
  const value = order.map((station) => {
    const total = sum.get(station)!;
    const n = shape === "by-date" ? Math.max(1, dates.get(station)!.size) : 1;
    return { station, dailyBoardings: total / n };
  });
  const report = [
    `${value.length} station${value.length === 1 ? "" : "s"} with counts` +
      (shape === "by-date" ? " (daily mean over the dates given)" : shape === "by-hour" ? " (hours summed into one day)" : ""),
  ];
  if (skipped) report.push(`${skipped} row${skipped === 1 ? "" : "s"} skipped (missing station or non-numeric value)`);
  const total = byHour.reduce((a, b) => a + b, 0);
  let hourly: number[] | undefined;
  if (shape === "by-hour" && total > 0) {
    hourly = byHour.map((v) => v / total);
    report.push(`Hourly profile from ${value.length} station${value.length === 1 ? "" : "s"}' counts by hour: weekday demand takes this shape`);
  }
  return ok({ rows: value, ...(hourly ? { hourly } : {}) }, report);
}
