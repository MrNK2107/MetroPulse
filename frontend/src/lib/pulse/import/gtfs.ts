/**
 * GTFS static zip to stations. Only the stations survive: a feed of tens of
 * megabytes becomes a few kilobytes of names, coordinates and modes.
 *
 * Mode comes from the route types that serve a stop (stop_times -> trips ->
 * routes): subway or rail is metro, bus is feeder; metro wins when both.
 * Without stop_times.txt, the stop's name decides.
 */
import { strFromU8, unzipSync } from "fflate";
import { findColumn, parseCsv, toNumber } from "./csv";
import { fail, ok, ParseResult, Station } from "./types";
import type { ModeId } from "../siting";

const MAX_KM = 60;
const DUP_KM = 0.15;
const KM_PER_DEG_LAT = 110.57;

const NEEDED = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt"];

function fileKey(files: Record<string, Uint8Array>, name: string): string | undefined {
  return Object.keys(files).find((k) => k === name || k.endsWith("/" + name));
}

function table(files: Record<string, Uint8Array>, name: string) {
  const key = fileKey(files, name);
  return key ? parseCsv(strFromU8(files[key])) : null;
}

/**
 * stop_times.txt is by far the largest file (millions of rows in a city bus feed). Only
 * trip_id and stop_id are needed, so it is scanned line by line without building a full table;
 * a line with a quote character falls back to the full CSV reader.
 */
function stopTripPairs(files: Record<string, Uint8Array>): { pairs: [string, string][]; header: string[] } | null {
  const key = fileKey(files, "stop_times.txt");
  if (!key) return null;
  const text = strFromU8(files[key]);
  const firstBreak = text.indexOf("\n");
  const headerLine = (firstBreak < 0 ? text : text.slice(0, firstBreak)).replace(/^\uFEFF/, "");
  const header = parseCsv(headerLine + "\n").header;
  const iTrip = findColumn(header, ["trip_id"]);
  const iStop = findColumn(header, ["stop_id"]);
  const pairs: [string, string][] = [];
  if (iTrip < 0 || iStop < 0 || firstBreak < 0) return { pairs, header };
  let start = firstBreak + 1;
  const n = text.length;
  while (start < n) {
    let end = text.indexOf("\n", start);
    if (end < 0) end = n;
    let line = text.slice(start, end);
    start = end + 1;
    if (line.endsWith("\r")) line = line.slice(0, -1);
    if (line === "") continue;
    let fields: string[];
    if (line.indexOf('"') < 0) fields = line.split(",");
    else fields = parseCsv("a\n" + line + "\n").rows[0] ?? [];
    const trip = fields[iTrip];
    const stop = fields[iStop];
    if (trip !== undefined && stop !== undefined) pairs.push([trip.trim(), stop.trim()]);
  }
  return { pairs, header };
}

function normName(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

export function parseGtfsZip(bytes: Uint8Array, centre: [number, number]): ParseResult<Station[]> {
  let files: Record<string, Uint8Array>;
  try {
    // Inflate only the four files that matter; shapes.txt alone can be most of a feed.
    files = unzipSync(bytes, { filter: (f) => NEEDED.some((n) => f.name === n || f.name.endsWith("/" + n)) });
  } catch {
    return fail("This file is not a zip archive");
  }
  const stops = table(files, "stops.txt");
  if (!stops) return fail("No stops.txt in this zip; is it a GTFS static feed?");
  const iId = findColumn(stops.header, ["stop_id"]);
  const iName = findColumn(stops.header, ["stop_name"]);
  const iLat = findColumn(stops.header, ["stop_lat"]);
  const iLng = findColumn(stops.header, ["stop_lon"]);
  const iType = findColumn(stops.header, ["location_type"]);
  const iParent = findColumn(stops.header, ["parent_station"]);
  if (iId < 0 || iName < 0 || iLat < 0 || iLng < 0) return fail("stops.txt needs stop_id, stop_name, stop_lat and stop_lon");

  // Which route types serve each stop (through stop_times -> trips -> routes).
  const routeType = new Map<string, number>();
  const tripRoute = new Map<string, string>();
  const stopTypes = new Map<string, Set<number>>();
  const routes = table(files, "routes.txt");
  const trips = table(files, "trips.txt");
  const stopTimes = stopTripPairs(files);
  const report: string[] = [];
  if (routes && trips && stopTimes) {
    const rId = findColumn(routes.header, ["route_id"]);
    const rType = findColumn(routes.header, ["route_type"]);
    for (const r of routes.rows) {
      const t = toNumber(r[rType]);
      if (rId >= 0 && t !== null) routeType.set(r[rId], t);
    }
    const tTrip = findColumn(trips.header, ["trip_id"]);
    const tRoute = findColumn(trips.header, ["route_id"]);
    for (const r of trips.rows) if (tTrip >= 0 && tRoute >= 0) tripRoute.set(r[tTrip], r[tRoute]);
    for (const [trip, stop] of stopTimes.pairs) {
      const rt = routeType.get(tripRoute.get(trip) ?? "");
      if (rt === undefined) continue;
      let set = stopTypes.get(stop);
      if (!set) stopTypes.set(stop, (set = new Set()));
      set.add(rt);
    }
  } else {
    report.push("No stop_times.txt, trips.txt or routes.txt: modes guessed from stop names (metro if the name says metro or station)");
  }

  // Children carry their parent's id so the parent's mode can include them.
  const childrenOf = new Map<string, string[]>();
  for (const r of stops.rows) {
    const p = iParent >= 0 ? (r[iParent] ?? "").trim() : "";
    if (p) childrenOf.set(p, [...(childrenOf.get(p) ?? []), r[iId]]);
  }

  const [cLat, cLng] = centre;
  const kx = 111.32 * Math.cos((cLat * Math.PI) / 180);
  const kept: Station[] = [];
  let far = 0;
  let merged = 0;
  let children = 0;
  for (const r of stops.rows) {
    const type = iType >= 0 ? (r[iType] ?? "").trim() : "";
    const parent = iParent >= 0 ? (r[iParent] ?? "").trim() : "";
    if (type !== "" && type !== "0" && type !== "1") continue; // entrances, nodes, boarding areas
    if (type !== "1" && parent) {
      children++;
      continue;
    }
    const name = (r[iName] ?? "").trim();
    const lat = toNumber(r[iLat]);
    const lng = toNumber(r[iLng]);
    if (!name || lat === null || lng === null) continue;
    if (Math.hypot((lng - cLng) * kx, (lat - cLat) * KM_PER_DEG_LAT) > MAX_KM) {
      far++;
      continue;
    }
    // Any route type seen at the station or its child platforms counts.
    const types = new Set<number>();
    for (const id of [r[iId], ...(childrenOf.get(r[iId]) ?? [])]) for (const t of stopTypes.get(id) ?? []) types.add(t);
    const mode: ModeId =
      types.size > 0 ? (types.has(1) || types.has(2) ? "metro" : "feeder") : /metro|station/i.test(name) ? "metro" : "feeder";
    const key = normName(name);
    const dup = kept.find(
      (s) => normName(s.name) === key && Math.hypot((s.lng - lng) * kx, (s.lat - lat) * KM_PER_DEG_LAT) <= DUP_KM
    );
    if (dup) {
      merged++;
      if (mode === "metro") dup.mode = "metro";
      continue;
    }
    kept.push({ name, lat, lng, mode });
  }
  if (kept.length === 0) return fail("No stations within 60 km of the city centre in stops.txt");
  const metro = kept.filter((s) => s.mode === "metro").length;
  report.unshift(`${kept.length} stations read (${metro} metro, ${kept.length - metro} bus)`);
  if (far) report.push(`${far} stop${far === 1 ? "" : "s"} more than ${MAX_KM} km from the centre dropped`);
  if (merged) report.push(`${merged} duplicate stop${merged === 1 ? "" : "s"} merged (same name within ${DUP_KM * 1000} m)`);
  if (children) report.push(`${children} platform${children === 1 ? "" : "s"} folded into their parent stations`);
  return ok(kept, report);
}
