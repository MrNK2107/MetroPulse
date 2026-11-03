/**
 * Stations CSV: `name, lat, lng[, mode]`. Header names are matched
 * case-insensitively with the usual synonyms.
 */
import { findColumn, parseCsv, toNumber } from "./csv";
import { fail, modeFromWord, ok, ParseResult, Station } from "./types";

export const NAME_COLUMNS = ["name", "station", "stop_name", "stop"];
export const LAT_COLUMNS = ["lat", "latitude", "stop_lat", "y"];
export const LNG_COLUMNS = ["lng", "lon", "long", "longitude", "stop_lon", "x"];
export const MODE_COLUMNS = ["mode", "type"];

export function parseStationsCsv(text: string): ParseResult<Station[]> {
  const { header, rows } = parseCsv(text);
  const iName = findColumn(header, NAME_COLUMNS);
  const iLat = findColumn(header, LAT_COLUMNS);
  const iLng = findColumn(header, LNG_COLUMNS);
  const iMode = findColumn(header, MODE_COLUMNS);
  if (iName < 0) return fail("No name column (expected one of: name, station, stop_name)");
  if (iLat < 0) return fail("No lat column (expected one of: lat, latitude)");
  if (iLng < 0) return fail("No lng column (expected one of: lng, lon, longitude)");

  const stations: Station[] = [];
  let skipped = 0;
  for (const r of rows) {
    const name = (r[iName] ?? "").trim();
    const lat = toNumber(r[iLat]);
    const lng = toNumber(r[iLng]);
    if (!name || lat === null || lng === null || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
      skipped++;
      continue;
    }
    stations.push({ name, lat, lng, mode: modeFromWord(iMode >= 0 ? r[iMode] : undefined) });
  }
  if (stations.length === 0) return fail("No usable rows: each row needs a name and numeric lat and lng");
  const report = [`${stations.length} station${stations.length === 1 ? "" : "s"} read`];
  if (skipped) report.push(`${skipped} row${skipped === 1 ? "" : "s"} skipped (missing name or non-numeric coordinates)`);
  if (iMode < 0) report.push("No mode column: every station treated as a metro station");
  return ok(stations, report);
}
