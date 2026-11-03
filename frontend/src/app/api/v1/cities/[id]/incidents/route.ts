import { detectIncidents } from "@/lib/pulse/alerts";
import { dayHourLabel } from "@/lib/pulse/time";
import { ok, preflight, withCity } from "@/lib/api/envelope";

export const revalidate = 3600;

export function GET(_req: Request, { params }: { params: { id: string } }) {
  return withCity(params.id, (model) => {
    const incidents = detectIncidents(model).map(({ cells, centroid: _centroid, ...rest }) => ({
      ...rest,
      hexagons: cells.length,
      peakLabel: dayHourLabel(rest.peakHour),
    }));
    return ok(incidents, { count: incidents.length, week: "sample" });
  });
}

export const OPTIONS = preflight;
