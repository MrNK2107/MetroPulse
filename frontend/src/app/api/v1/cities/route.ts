import { listCities } from "@/lib/pulse/geo";
import { ok, preflight } from "@/lib/api/envelope";

export const dynamic = "force-static";
export const revalidate = 3600;

export function GET(_req?: Request) {
  return ok(
    listCities().map((c) => ({ id: c.id, name: c.name, state: c.state, population: c.population, centre: { lat: c.center[0], lng: c.center[1] }, metro: c.metro })),
    { count: listCities().length }
  );
}

export const OPTIONS = preflight;
