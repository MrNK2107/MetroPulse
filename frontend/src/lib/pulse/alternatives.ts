/**
 * The alternatives table: one row per option, in the columns a DPR
 * alternatives-analysis annex uses. CSV for spreadsheets, Markdown for
 * documents.
 */
import { csvField } from "./export";
import type { NetworkResult, Scenario } from "./scenario";

export const ALTERNATIVES_COLUMNS = [
  "Option",
  "Mode",
  "Stations",
  "Length (km)",
  "Daily boardings",
  "New share",
  "Walk-band coverage after",
  "Capital cost (₹ cr)",
  "Cost per daily boarding (₹ lakh)",
  "Score",
] as const;

export interface AlternativeRow {
  label: string;
  s: Scenario;
  r: NetworkResult;
}

export function alternativeValues({ label, s, r }: AlternativeRow): (string | number)[] {
  return [
    `${label}: ${s.name}`,
    s.mode,
    s.stations.length,
    r.lengthKm.toFixed(1),
    Math.round(r.boardings),
    `${Math.round(r.newShare * 100)}%`,
    `${(r.coverageAfter * 100).toFixed(1)}%`,
    Math.round(r.costCr),
    r.costPerBoardingLakh.toFixed(2),
    r.score,
  ];
}

export function alternativesCsv(rows: AlternativeRow[]): string {
  const lines = [ALTERNATIVES_COLUMNS.map(csvField).join(",")];
  for (const row of rows) lines.push(alternativeValues(row).map(csvField).join(","));
  return lines.join("\n") + "\n";
}

export function alternativesMarkdown(rows: AlternativeRow[]): string {
  const cell = (v: string | number) => String(v).replace(/\|/g, "\\|");
  const lines = [
    `| ${ALTERNATIVES_COLUMNS.join(" | ")} |`,
    `|${ALTERNATIVES_COLUMNS.map(() => " --- |").join("")}`,
    ...rows.map((row) => `| ${alternativeValues(row).map(cell).join(" | ")} |`),
  ];
  return lines.join("\n") + "\n";
}
