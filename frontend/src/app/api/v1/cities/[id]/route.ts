import { citySummary } from "@/lib/pulse/summary";
import { ok, preflight, withCity } from "@/lib/api/envelope";

export const revalidate = 3600;

export function GET(_req: Request, { params }: { params: { id: string } }) {
  return withCity(params.id, (model) => {
    const s = citySummary(model);
    // Incidents carry hexagon index lists; the summary keeps the explanation only.
    const topIncidents = s.topIncidents.map(({ cells: _cells, centroid: _centroid, ...rest }) => rest);
    return ok({ ...s, topIncidents });
  });
}

export const OPTIONS = preflight;
