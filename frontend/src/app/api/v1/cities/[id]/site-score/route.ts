import { MODES, ModeId, existingCoverage, scoreSite } from "@/lib/pulse/siting";
import { placeName } from "@/lib/pulse/placeName";
import { fail, nearCity, numberParam, ok, preflight, withCity } from "@/lib/api/envelope";

export function GET(req: Request, { params }: { params: { id: string } }) {
  const url = new URL(req.url);
  const lat = numberParam(url, "lat");
  const lng = numberParam(url, "lng");
  const mode = (url.searchParams.get("mode") ?? "metro") as ModeId;
  if (lat === null || lng === null) return fail(400, "bad_request", "lat and lng are required numeric query parameters");
  if (!(mode in MODES)) return fail(400, "bad_request", `mode must be one of ${Object.keys(MODES).join(", ")}`);
  return withCity(params.id, (model) => {
    if (!nearCity(model, lat, lng)) return fail(400, "bad_request", "The point is more than 100 km from the city centre");
    const site = model.grid.project(lat, lng);
    const { walkCells: _w, feederCells: _f, site: _s, ...r } = scoreSite(model, site, mode, existingCoverage(model), model.calibration);
    return ok({ ...r, lat, lng, place: placeName(model, site) });
  });
}

export const OPTIONS = preflight;
