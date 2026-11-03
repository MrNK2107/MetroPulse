/**
 * A city boundary from GeoJSON: the outer ring of the largest polygon, holes
 * dropped, as a closed [lng, lat] ring. A file whose polygon sits far from the
 * city is almost always the wrong file, so it is rejected with the distance.
 */
import { fail, ok, ParseResult } from "./types";

export type LngLat = [number, number];

const MAX_CENTRE_KM = 150;
/** A city planning area: Greater Mumbai is about 600 km², Delhi about 1,500 km². */
export const MIN_AREA_KM2 = 5;
export const MAX_AREA_KM2 = 10000;
/** Rings with more vertices than this are thinned; the grid and the map need far fewer. */
export const MAX_VERTICES = 5000;
const KM_PER_DEG_LAT = 110.57;

function kmPerDegLng(lat: number): number {
  return 111.32 * Math.cos((lat * Math.PI) / 180);
}

/** Planar shoelace area in km², using the ring's mean latitude for the longitude scale. */
export function ringAreaKm2(ring: LngLat[]): number {
  if (ring.length < 3) return 0;
  const lat0 = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  const kx = kmPerDegLng(lat0);
  let a = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x1, y1] = ring[j];
    const [x2, y2] = ring[i];
    a += x1 * kx * (y2 * KM_PER_DEG_LAT) - x2 * kx * (y1 * KM_PER_DEG_LAT);
  }
  return Math.abs(a) / 2;
}

type Geometry = { type: string; coordinates?: unknown; geometries?: Geometry[] };

function collectRings(g: Geometry | undefined, out: LngLat[][]): void {
  if (!g || typeof g !== "object") return;
  if (g.type === "Polygon" && Array.isArray(g.coordinates)) {
    const outer = (g.coordinates as unknown[])[0];
    if (Array.isArray(outer)) out.push(outer as LngLat[]);
  } else if (g.type === "MultiPolygon" && Array.isArray(g.coordinates)) {
    for (const poly of g.coordinates as unknown[]) {
      const outer = Array.isArray(poly) ? (poly as unknown[])[0] : undefined;
      if (Array.isArray(outer)) out.push(outer as LngLat[]);
    }
  } else if (g.type === "GeometryCollection" && Array.isArray(g.geometries)) {
    for (const x of g.geometries) collectRings(x, out);
  }
}

function ringsOf(doc: unknown): LngLat[][] {
  const out: LngLat[][] = [];
  if (!doc || typeof doc !== "object") return out;
  const d = doc as { type?: string; features?: unknown[]; geometry?: Geometry };
  if (d.type === "FeatureCollection" && Array.isArray(d.features)) {
    for (const f of d.features) ringsOf(f).forEach((r) => out.push(r));
  } else if (d.type === "Feature") {
    collectRings(d.geometry, out);
  } else {
    collectRings(d as Geometry, out);
  }
  return out;
}

function validPoint(p: unknown): p is LngLat {
  return (
    Array.isArray(p) &&
    typeof p[0] === "number" &&
    typeof p[1] === "number" &&
    Number.isFinite(p[0]) &&
    Number.isFinite(p[1]) &&
    Math.abs(p[0]) <= 180 &&
    Math.abs(p[1]) <= 90
  );
}

export function parseBoundaryGeoJson(text: string, centre: [number, number]): ParseResult<LngLat[]> {
  let doc: unknown;
  try {
    doc = JSON.parse(text);
  } catch {
    return fail("Not valid JSON");
  }
  const rings = ringsOf(doc);
  if (rings.length === 0) return fail("No Polygon or MultiPolygon found in this GeoJSON");

  let best: LngLat[] | null = null;
  let bestArea = -1;
  let invalid = 0;
  for (const raw of rings) {
    if (!raw.every(validPoint)) {
      invalid++;
      continue;
    }
    let ring = raw.map((p) => [p[0], p[1]] as LngLat);
    const first = ring[0];
    const last = ring[ring.length - 1];
    if (first[0] !== last[0] || first[1] !== last[1]) ring = [...ring, [first[0], first[1]]];
    if (ring.length < 4) {
      invalid++;
      continue;
    }
    const area = ringAreaKm2(ring);
    if (area > bestArea) {
      bestArea = area;
      best = ring;
    }
  }
  if (!best) return fail(invalid ? "Every ring has fewer than 4 points or coordinates out of range" : "No usable ring");

  let simplifiedFrom = 0;
  if (best.length - 1 > MAX_VERTICES) {
    const open = best.slice(0, -1);
    const step = Math.ceil(open.length / MAX_VERTICES);
    const thin = open.filter((_, i) => i % step === 0);
    simplifiedFrom = open.length;
    best = [...thin, thin[0]];
    bestArea = ringAreaKm2(best);
  }
  if (bestArea < MIN_AREA_KM2) {
    return fail(`This boundary covers only ${bestArea.toFixed(1)} km²; a city planning area is usually hundreds of km². Is it the right feature?`);
  }
  if (bestArea > MAX_AREA_KM2) {
    return fail(
      `This boundary covers ${Math.round(bestArea).toLocaleString("en-IN")} km², above the ${MAX_AREA_KM2.toLocaleString("en-IN")} km² limit. Is it a state or a district?`
    );
  }

  const [cLat, cLng] = centre;
  const n = best.length - 1;
  const mLng = best.slice(0, n).reduce((s, p) => s + p[0], 0) / n;
  const mLat = best.slice(0, n).reduce((s, p) => s + p[1], 0) / n;
  const km = Math.hypot((mLng - cLng) * kmPerDegLng(cLat), (mLat - cLat) * KM_PER_DEG_LAT);
  if (km > MAX_CENTRE_KM) return fail(`This boundary is about ${Math.round(km)} km from the city centre; is it the right file?`);

  const report = [`Boundary: ${Math.round(bestArea).toLocaleString("en-IN")} km², ${n} vertices`];
  if (simplifiedFrom) report.push(`Outline simplified from ${simplifiedFrom.toLocaleString("en-IN")} to ${n} vertices`);
  if (rings.length > 1) report.push(`${rings.length} polygons in the file; the largest was used`);
  if (invalid) report.push(`${invalid} ring${invalid === 1 ? "" : "s"} ignored (too few points or coordinates out of range)`);
  return ok(best, report);
}
