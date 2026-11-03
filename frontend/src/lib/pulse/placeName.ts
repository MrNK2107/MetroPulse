/** Names for a point on the grid, relative to the nearest configured anchor or station. */
import type { Point } from "./geo";
import type { CityModel } from "./model";

const COMPASS = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"];

export function placeName(model: CityModel, p: Point): string {
  const { anchor, km } = model.nearestAnchor(p);
  if (km < 0.35) return anchor.name;
  const a = model.grid.project(anchor.lat, anchor.lng);
  const ang = (Math.atan2(p.y - a.y, p.x - a.x) * 180) / Math.PI;
  const dir = COMPASS[Math.round(((ang + 360) % 360) / 45) % 8];
  return `${km.toFixed(1)} km ${dir} of ${anchor.name}`;
}

/** "near T Nagar", but "0.8 km N of Chennai Central" (that is already a position). */
export function nearPlace(name: string): string {
  return /^\d/.test(name) ? name : `near ${name}`;
}
