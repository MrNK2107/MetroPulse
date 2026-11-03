/**
 * Builds a small synthetic GTFS zip in memory for tests. Twelve stops around a
 * centre: six on a metro line (route_type 1), six on a bus route (route_type 3).
 * Nothing here is copied from a real feed.
 */
import { strToU8, zipSync } from "fflate";

export interface GtfsFixtureOptions {
  centre?: [number, number]; // [lat, lng]
  withStopTimes?: boolean;
  extraStops?: string[]; // extra lines for stops.txt
}

export function gtfsStops(centre: [number, number] = [13.0827, 80.2707]): { id: string; name: string; lat: number; lng: number; metro: boolean }[] {
  const [lat, lng] = centre;
  const out = [];
  for (let k = 0; k < 6; k++) out.push({ id: `M${k}`, name: `Metro Stop ${k}`, lat: lat + 0.01 * k, lng: lng + 0.005 * k, metro: true });
  for (let k = 0; k < 6; k++) out.push({ id: `B${k}`, name: `Bus Halt ${k}`, lat: lat - 0.01 * k, lng: lng - 0.008 * k, metro: false });
  return out;
}

export function buildGtfsZip(opts: GtfsFixtureOptions = {}): Uint8Array {
  const { centre = [13.0827, 80.2707], withStopTimes = true, extraStops = [] } = opts;
  const stops = gtfsStops(centre);
  const files: Record<string, Uint8Array> = {};
  files["stops.txt"] = strToU8(
    ["stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station", ...stops.map((s) => `${s.id},"${s.name}",${s.lat},${s.lng},0,`), ...extraStops].join("\r\n") + "\r\n"
  );
  files["routes.txt"] = strToU8("route_id,route_short_name,route_type\r\nR1,Blue,1\r\nR2,500C,3\r\n");
  files["trips.txt"] = strToU8("route_id,service_id,trip_id\r\nR1,WK,T1\r\nR2,WK,T2\r\n");
  if (withStopTimes) {
    const rows = ["trip_id,arrival_time,departure_time,stop_id,stop_sequence"];
    stops.forEach((s, k) => rows.push(`${s.metro ? "T1" : "T2"},08:00:00,08:00:00,${s.id},${k}`));
    files["stop_times.txt"] = strToU8(rows.join("\r\n") + "\r\n");
  }
  files["agency.txt"] = strToU8("﻿agency_id,agency_name,agency_url,agency_timezone\r\nX,Test Transit,https://example.invalid,Asia/Kolkata\r\n");
  return zipSync(files, { level: 0 });
}
