/**
 * Alerts that explain themselves.
 *
 * 1. For every hexagon and hour of the week, take the same hour in the four
 *    trailing weeks and compute the median and the MAD (median absolute
 *    deviation). That is the baseline.
 * 2. Flag a hex-hour when the current week is far from it: robust z >= 4 and
 *    the change is at least 30% of the median.
 * 3. Join flagged hex-hours of the same sign that touch in space (neighbouring
 *    hexagons, same hour) or in time (same hexagon, next hour) into incidents.
 *    Clusters of fewer than 3 hex-hours are dropped as noise.
 * 4. Explain each incident with a fixed, auditable rule trace: what, where,
 *    how big, the likely cause and what to check.
 */
import type { Point } from "./geo";
import { CityModel, DAYS, dayHourLabel, HOURS_PER_WEEK, hourLabel } from "./model";

export const Z_THRESHOLD = 4;
export const MIN_RELATIVE_CHANGE = 0.3;
export const MIN_CLUSTER = 3;

export interface Incident {
  id: string;
  kind: "surge" | "drop";
  cells: number[];
  hexHours: number;
  startHour: number;
  endHour: number;
  peakHour: number;
  excessTrips: number;
  peakRatio: number;
  centroid: Point;
  anchor: { name: string; type: string; km: number };
  headline: string;
  explanation: string;
  likelyCause: string;
  whatToCheck: string;
  ruleTrace: string[];
}

export function robustStats(values: number[]): { median: number; mad: number } {
  const med = median(values);
  return { median: med, mad: median(values.map((v) => Math.abs(v - med))) };
}

/** Median of exactly four numbers, without allocating (hot loop: cells x 168). */
export function median4(a: number, b: number, c: number, d: number): number {
  // sort the pairs, then the middle two of four are max(lo) and min(hi)
  const lo1 = a < b ? a : b;
  const hi1 = a < b ? b : a;
  const lo2 = c < d ? c : d;
  const hi2 = c < d ? d : c;
  const midLo = lo1 > lo2 ? lo1 : lo2;
  const midHi = hi1 < hi2 ? hi1 : hi2;
  return (midLo + midHi) / 2;
}

function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

const LEISURE = new Set(["cbd", "commercial", "tourism", "heritage", "trade", "transport"]);
const WORK = new Set(["industrial", "tech_park", "sez", "technology", "biotech_park", "port", "economic", "it"]);

function fmt(n: number): string {
  return Math.round(n).toLocaleString("en-IN");
}

function explain(
  kind: "surge" | "drop",
  peakHour: number,
  anchor: { name: string; type: string; km: number }
): { cause: string; check: string; rule: string } {
  const hr = peakHour % 24;
  const day = DAYS[Math.floor(peakHour / 24)];
  const where = anchor.name;
  const peakWindow = (hr >= 6 && hr <= 11) || (hr >= 16 && hr <= 21);
  if (kind === "surge" && hr >= 17 && hr <= 23 && LEISURE.has(anchor.type))
    return {
      cause: `A crowd release after a large event (a concert, match or festival gathering) at or near ${where}.`,
      check: `Event permits and police bandobast for ${day} evening, and whether extra trains or buses ran.`,
      rule: "evening surge (17:00-23:00) next to a CBD, leisure or transport anchor -> event",
    };
  if (kind === "surge" && hr >= 10 && hr <= 17 && WORK.has(anchor.type))
    return {
      cause: `A shift change or a large intake at employers around ${where}.`,
      check: `Employer shift rosters and any new tenant or recruitment drive at ${where}.`,
      rule: "daytime surge (10:00-17:00) next to an employment anchor -> shift change",
    };
  if (kind === "surge" && anchor.type === "transport")
    return {
      cause: `A rail or bus disruption elsewhere pushing riders through ${where}.`,
      check: "Service alerts from the rail and bus operators for that window.",
      rule: "surge next to a transport hub outside the event window -> diverted riders",
    };
  if (kind === "drop" && peakWindow)
    return {
      cause: `A supply disruption cutting peak-hour trips around ${where}: waterlogging, a road closure or a service suspension.`,
      check: `Rainfall readings, traffic-police diversions and operator suspensions for ${day} ${hourLabel(hr)}.`,
      rule: "drop inside a commute peak (06:00-11:00 or 16:00-21:00) -> supply disruption",
    };
  if (kind === "drop")
    return {
      cause: `Unusual quiet near ${where}: a local holiday, bandh or closure.`,
      check: "The local holiday calendar and news for closures.",
      rule: "drop outside the commute peaks -> holiday or closure",
    };
  return {
    cause: `Unusual activity near ${where} that matches no known pattern.`,
    check: "A field check, then compare with next week before acting.",
    rule: "no rule matched -> unexplained",
  };
}

export function detectIncidents(model: CityModel): Incident[] {
  const { grid, baselineWeeks, thisWeek } = model;
  const n = grid.cells.length;
  const H = HOURS_PER_WEEK;
  const sign = new Int8Array(n * H);
  const delta = new Float32Array(n * H);
  const med = new Float32Array(n * H);
  if (baselineWeeks.length !== 4) throw new Error("detectIncidents expects exactly four baseline weeks");
  const [w0, w1, w2, w3] = baselineWeeks;

  for (let i = 0; i < n * H; i++) {
    const a = w0[i];
    const b = w1[i];
    const c = w2[i];
    const e = w3[i];
    const m = median4(a, b, c, e);
    const mad = median4(Math.abs(a - m), Math.abs(b - m), Math.abs(c - m), Math.abs(e - m));
    const d = thisWeek[i] - m;
    const scale = Math.max(1.4826 * mad, 0.08 * m, 3);
    med[i] = m;
    delta[i] = d;
    if (Math.abs(d) / scale >= Z_THRESHOLD && Math.abs(d) >= MIN_RELATIVE_CHANGE * m) sign[i] = d > 0 ? 1 : -1;
  }

  // Union-find over flagged hex-hours.
  const parent = new Int32Array(n * H).fill(-1);
  const find = (x: number): number => {
    while (parent[x] !== x) {
      parent[x] = parent[parent[x]];
      x = parent[x];
    }
    return x;
  };
  const union = (a: number, b: number) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent[ra] = rb;
  };
  for (let i = 0; i < n * H; i++) if (sign[i]) parent[i] = i;
  for (let c = 0; c < n; c++) {
    const ns = grid.neighbours(c);
    for (let h = 0; h < H; h++) {
      const i = c * H + h;
      if (!sign[i]) continue;
      if (h + 1 < H && sign[i + 1] === sign[i]) union(i, i + 1);
      for (const nb of ns) {
        const j = nb * H + h;
        if (sign[j] === sign[i]) union(i, j);
      }
    }
  }

  const groups = new Map<number, number[]>();
  for (let i = 0; i < n * H; i++) {
    if (!sign[i]) continue;
    const r = find(i);
    const g = groups.get(r);
    if (g) g.push(i);
    else groups.set(r, [i]);
  }

  const incidents: Incident[] = [];
  for (const members of Array.from(groups.values())) {
    if (members.length < MIN_CLUSTER) continue;
    const kind = sign[members[0]] > 0 ? "surge" : "drop";
    const cellSet = new Set<number>();
    const byHourDelta = new Map<number, number>();
    const byHourMed = new Map<number, number>();
    let excess = 0;
    let start = H;
    let end = 0;
    for (const i of members) {
      const c = Math.floor(i / H);
      const h = i % H;
      cellSet.add(c);
      excess += delta[i];
      start = Math.min(start, h);
      end = Math.max(end, h);
      byHourDelta.set(h, (byHourDelta.get(h) ?? 0) + delta[i]);
      byHourMed.set(h, (byHourMed.get(h) ?? 0) + med[i]);
    }
    let peakHour = start;
    for (const [h, d] of Array.from(byHourDelta.entries()))
      if (Math.abs(d) > Math.abs(byHourDelta.get(peakHour)!)) peakHour = h;
    const peakMed = byHourMed.get(peakHour)!;
    // a cluster on near-empty hexagons can have a ~0 median; keep the ratio finite
    const peakRatio = (peakMed + byHourDelta.get(peakHour)!) / Math.max(peakMed, 1);

    const cells = Array.from(cellSet);
    const centroid = {
      x: cells.reduce((a, c) => a + grid.cells[c].x, 0) / cells.length,
      y: cells.reduce((a, c) => a + grid.cells[c].y, 0) / cells.length,
    };
    const near = model.nearestAnchor(centroid);
    const anchor = { name: near.anchor.name, type: near.anchor.type, km: near.km };
    const { cause, check, rule } = explain(kind, peakHour, anchor);
    const hours = end - start + 1;
    const window = `${dayHourLabel(start)}-${hourLabel(end + 1)}`;
    const ratioText = kind === "surge" ? `${peakRatio.toFixed(1)}x` : `${Math.round(peakRatio * 100)}% of`;

    incidents.push({
      id: `${kind}-${start}-${cells[0]}`,
      kind,
      cells,
      hexHours: members.length,
      startHour: start,
      endHour: end,
      peakHour,
      excessTrips: excess,
      peakRatio,
      centroid,
      anchor,
      headline: `${kind === "surge" ? "Surge" : "Drop"} near ${anchor.name}, ${window}`,
      explanation:
        `Trips across ${cells.length} hexagons ran at ${ratioText} the four-week same-hour median at the peak ` +
        `(${dayHourLabel(peakHour)}): about ${fmt(Math.abs(excess))} ${kind === "surge" ? "extra" : "missing"} trips over ${hours} hour${hours > 1 ? "s" : ""}.`,
      likelyCause: cause,
      whatToCheck: check,
      ruleTrace: [
        `baseline = median of the same hour in 4 trailing weeks; spread = MAD`,
        `flag when |robust z| >= ${Z_THRESHOLD} and |change| >= ${MIN_RELATIVE_CHANGE * 100}% of median`,
        `${members.length} flagged hex-hours joined by adjacency in space and time`,
        `direction = ${kind}; peak at ${dayHourLabel(peakHour)}`,
        `nearest anchor = ${anchor.name} (${anchor.type}, ${anchor.km.toFixed(1)} km from the centroid)`,
        `rule: ${rule}`,
      ],
    });
  }
  incidents.sort((a, b) => Math.abs(b.excessTrips) - Math.abs(a.excessTrips));
  return incidents;
}
