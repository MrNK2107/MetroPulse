/**
 * Survey zones (traffic-analysis zones, wards, census tracts): one row per zone
 * with a centroid, residents and jobs. With zones loaded, the desk's residents
 * and jobs come from these figures instead of the synthetic field.
 */
import { findColumn, parseCsv, toNumber } from "./csv";
import { fail, ok, ParseResult } from "./types";

export interface Zone {
  name: string;
  lat: number;
  lng: number;
  residents: number;
  jobs: number;
  /** Spread of the zone around its centroid; defaults to 1.2 km in the model. */
  radiusKm?: number;
}

const NAME = ["zone", "name", "zone_id", "taz", "ward", "id"];
const LAT = ["lat", "latitude", "y"];
const LNG = ["lng", "lon", "long", "longitude", "x"];
const RESIDENTS = ["residents", "population", "pop", "households_persons", "persons"];
const JOBS = ["jobs", "employment", "workers", "workplaces"];
const RADIUS = ["radius_km", "radius"];

export function parseZonesCsv(text: string): ParseResult<Zone[]> {
  const { header, rows } = parseCsv(text);
  const iName = findColumn(header, NAME);
  const iLat = findColumn(header, LAT);
  const iLng = findColumn(header, LNG);
  const iRes = findColumn(header, RESIDENTS);
  const iJobs = findColumn(header, JOBS);
  const iRad = findColumn(header, RADIUS);
  if (iLat < 0 || iLng < 0) return fail("Zones need lat and lng columns (the zone centroid)");
  if (iRes < 0) return fail("No residents column (expected one of: residents, population)");

  const zones: Zone[] = [];
  let skipped = 0;
  rows.forEach((r, k) => {
    const lat = toNumber(r[iLat]);
    const lng = toNumber(r[iLng]);
    const residents = toNumber(r[iRes]);
    const jobs = iJobs >= 0 ? toNumber(r[iJobs]) ?? 0 : 0;
    if (lat === null || lng === null || residents === null || residents < 0 || jobs < 0 || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
      skipped++;
      return;
    }
    const name = (iName >= 0 ? r[iName] : "")?.trim() || `Zone ${k + 1}`;
    const radius = iRad >= 0 ? toNumber(r[iRad]) : null;
    zones.push({ name, lat, lng, residents, jobs, ...(radius !== null && radius > 0 ? { radiusKm: radius } : {}) });
  });
  if (zones.length === 0) return fail("No usable rows: each zone needs numeric lat, lng and residents");
  const res = zones.reduce((a, z) => a + z.residents, 0);
  const jobs = zones.reduce((a, z) => a + z.jobs, 0);
  const report = [
    `${zones.length} zones read: ${Math.round(res).toLocaleString("en-IN")} residents and ${Math.round(jobs).toLocaleString("en-IN")} jobs`,
  ];
  if (skipped) report.push(`${skipped} row${skipped === 1 ? "" : "s"} skipped (non-numeric or negative values)`);
  if (iJobs < 0) report.push("No jobs column: zones carry residents only");
  return ok(zones, report);
}
