/**
 * The JSON envelope every /api/v1 route answers with, matching the backend:
 *   { success, data, error, meta }
 * Responses are public and cacheable for an hour; GET is open to any origin.
 */
import { getCity } from "@/lib/pulse/geo";
import { getCityModel } from "@/lib/pulse/model";
import type { CityModel } from "@/lib/pulse/model";

export const API_VERSION = "v1";
export const MAX_AGE = 3600;

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function meta(extra: Record<string, unknown> = {}) {
  return { version: API_VERSION, model: "sample", note: "Numbers come from the MetroPulse sample city model and are illustrative.", ...extra };
}

export function ok<T>(data: T, extra: Record<string, unknown> = {}): Response {
  return Response.json(
    { success: true, data, error: null, meta: meta(extra) },
    { status: 200, headers: { ...CORS, "Cache-Control": `public, max-age=${MAX_AGE}` } }
  );
}

export function fail(status: number, code: string, message: string): Response {
  return Response.json(
    { success: false, data: null, error: { code, message }, meta: meta() },
    { status, headers: { ...CORS, "Cache-Control": "no-store" } }
  );
}

export function preflight(): Response {
  return new Response(null, { status: 204, headers: CORS });
}

/** Resolve a city id to its model, or answer 404. */
export function withCity(id: string, fn: (model: CityModel) => Response): Response {
  const city = getCity(id);
  if (!city) return fail(404, "city_not_found", `No city with id "${id}". GET /api/v1/cities lists them.`);
  return fn(getCityModel(city));
}

export function numberParam(url: URL, name: string): number | null {
  const raw = url.searchParams.get(name);
  if (raw === null || raw.trim() === "") return null;
  const v = Number(raw);
  return Number.isFinite(v) ? v : null;
}

/** Within 100 km of the city centre, like the shared-link decoder. */
export function nearCity(model: CityModel, lat: number, lng: number): boolean {
  const [cLat, cLng] = model.city.center;
  const kx = 111.32 * Math.cos((cLat * Math.PI) / 180);
  return Math.hypot((lng - cLng) * kx, (lat - cLat) * 110.57) <= 100;
}
