import { MODES, ModeId, existingCoverage, suggestSites } from "@/lib/pulse/siting";
import { placeName } from "@/lib/pulse/placeName";
import { fail, numberParam, ok, preflight, withCity } from "@/lib/api/envelope";

export function GET(req: Request, { params }: { params: { id: string } }) {
  const url = new URL(req.url);
  const mode = (url.searchParams.get("mode") ?? "metro") as ModeId;
  if (!(mode in MODES)) return fail(400, "bad_request", `mode must be one of ${Object.keys(MODES).join(", ")}`);
  const k = Math.min(5, Math.max(1, Math.round(numberParam(url, "k") ?? 3)));
  return withCity(params.id, (model) => {
    const picks = suggestSites(model, mode, k, existingCoverage(model), model.calibration).map((p, rank) => {
      const cell = model.grid.cells[p.cell];
      const { lat, lng } = model.grid.unproject(cell);
      const { walkCells: _w, feederCells: _f, site: _s, ...r } = p.result;
      return { rank: rank + 1, lat: Math.round(lat * 1e4) / 1e4, lng: Math.round(lng * 1e4) / 1e4, place: placeName(model, cell), ...r };
    });
    return ok(picks, { mode, k });
  });
}

export const OPTIONS = preflight;
