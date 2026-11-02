import type { Incident } from "./alerts";
import { dayHourLabel } from "./model";

/** Quote a CSV field when it holds a comma, quote or newline (RFC 4180). */
export function csvField(v: string | number): string {
  const s = String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export const INCIDENT_CSV_HEADER = [
  "rank",
  "kind",
  "headline",
  "nearest_place",
  "start",
  "peak",
  "end",
  "hexagons",
  "hex_hours",
  "excess_trips",
  "peak_ratio",
  "likely_cause",
  "what_to_check",
] as const;

/** This week's incidents as CSV, one row per incident, in feed order (most severe first). */
export function incidentsToCsv(incidents: Incident[]): string {
  const rows = incidents.map((i, k) =>
    [
      k + 1,
      i.kind,
      i.headline,
      i.anchor.name,
      dayHourLabel(i.startHour),
      dayHourLabel(i.peakHour),
      dayHourLabel(i.endHour),
      i.cells.length,
      i.hexHours,
      Math.round(i.excessTrips),
      i.peakRatio.toFixed(2),
      i.likelyCause,
      i.whatToCheck,
    ]
      .map(csvField)
      .join(",")
  );
  return [INCIDENT_CSV_HEADER.join(","), ...rows].join("\r\n") + "\r\n";
}

/** Hand a text file to the browser as a download. No-op outside a browser. */
export function downloadText(filename: string, text: string, type = "text/csv;charset=utf-8"): void {
  if (typeof window === "undefined" || typeof URL.createObjectURL !== "function") return;
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/** One cell's 24 hours on the day containing `hour`, this week and baseline, for a sparkline. */
export function cellDay(
  thisWeek: Float32Array,
  baselineMean: Float32Array,
  cell: number,
  hour: number
): { now: number[]; base: number[]; at: number } {
  const day = Math.floor(hour / 24);
  const o = cell * 168 + day * 24;
  return {
    now: Array.from(thisWeek.subarray(o, o + 24)),
    base: Array.from(baselineMean.subarray(o, o + 24)),
    at: hour % 24,
  };
}
