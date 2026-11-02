/**
 * City catalogue and the hexagonal analysis grid.
 *
 * Cells are pointy-top hexagons on a local equirectangular projection (km),
 * sized to match H3 resolution 8 (about 0.74 km2 each). Coordinates are local
 * kilometres east (x) and north (y) of the city centre.
 */
import citiesJson from "@/data/cities.json";

export type AnchorType = string;

export interface Anchor {
  name: string;
  type: AnchorType;
  lat: number;
  lng: number;
  weight: number;
}

export interface City {
  id: string;
  name: string;
  state: string;
  center: [number, number]; // [lat, lng]
  population: number;
  metro: boolean;
  anchors: Anchor[];
  boundary: [number, number][]; // [lng, lat] ring
}

const CITIES = citiesJson as unknown as City[];

export function listCities(): City[] {
  return CITIES;
}

export function getCity(id: string): City | undefined {
  return CITIES.find((c) => c.id === id);
}

export interface Point {
  x: number;
  y: number;
}

export interface Cell extends Point {
  index: number;
  q: number;
  r: number;
}

/** H3 resolution 8 average hexagon area is 0.737 km2; edge = sqrt(2A / (3*sqrt(3))). */
export const H3_RES8_AREA_KM2 = 0.737;
export const EDGE_KM = Math.sqrt((2 * H3_RES8_AREA_KM2) / (3 * Math.sqrt(3)));
const SQRT3 = Math.sqrt(3);
const DIRS: [number, number][] = [
  [1, 0],
  [1, -1],
  [0, -1],
  [-1, 0],
  [-1, 1],
  [0, 1],
];

export function hexDistanceKm(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function pointInRing(x: number, y: number, ring: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i];
    const b = ring[j];
    if (a.y > y !== b.y > y && x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x) inside = !inside;
  }
  return inside;
}

export interface HexGrid {
  edgeKm: number;
  spacingKm: number;
  cellAreaKm2: number;
  cells: Cell[];
  boundary: Point[];
  project(lat: number, lng: number): Point;
  unproject(p: Point): { lat: number; lng: number };
  neighbours(index: number): number[];
  within(x: number, y: number, radiusKm: number): number[];
  cellAt(x: number, y: number): number | undefined;
  corners(cell: Point): Point[];
}

export function buildHexGrid(city: City, edgeKm = EDGE_KM): HexGrid {
  const [lat0, lng0] = city.center;
  // Rounded so the server render and the browser agree to the bit (Math.cos may differ in the last place).
  const kx = Math.round(111.32 * Math.cos((lat0 * Math.PI) / 180) * 1e9) / 1e9;
  const ky = 110.57;
  const project = (lat: number, lng: number): Point => ({ x: (lng - lng0) * kx, y: (lat - lat0) * ky });
  const unproject = (p: Point) => ({ lat: lat0 + p.y / ky, lng: lng0 + p.x / kx });
  const boundary = city.boundary.map(([lng, lat]) => project(lat, lng));

  const toXY = (q: number, r: number): Point => ({ x: edgeKm * SQRT3 * (q + r / 2), y: edgeKm * 1.5 * r });
  const toQR = (x: number, y: number): [number, number] => {
    // axial rounding via cube coordinates
    const qf = ((SQRT3 / 3) * x - y / 3) / edgeKm;
    const rf = ((2 / 3) * y) / edgeKm;
    const sf = -qf - rf;
    let q = Math.round(qf);
    let r = Math.round(rf);
    const s = Math.round(sf);
    const dq = Math.abs(q - qf);
    const dr = Math.abs(r - rf);
    const ds = Math.abs(s - sf);
    if (dq > dr && dq > ds) q = -r - s;
    else if (dr > ds) r = -q - s;
    return [q, r];
  };

  const xs = boundary.map((p) => p.x);
  const ys = boundary.map((p) => p.y);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const rMin = Math.floor(minY / (edgeKm * 1.5)) - 1;
  const rMax = Math.ceil(maxY / (edgeKm * 1.5)) + 1;

  const cells: Cell[] = [];
  const byKey = new Map<string, number>();
  for (let r = rMin; r <= rMax; r++) {
    const qMin = Math.floor(minX / (edgeKm * SQRT3) - r / 2) - 1;
    const qMax = Math.ceil(maxX / (edgeKm * SQRT3) - r / 2) + 1;
    for (let q = qMin; q <= qMax; q++) {
      const { x, y } = toXY(q, r);
      if (!pointInRing(x, y, boundary)) continue;
      byKey.set(`${q},${r}`, cells.length);
      cells.push({ index: cells.length, q, r, x, y });
    }
  }

  const spacingKm = edgeKm * SQRT3;
  const lookup = (q: number, r: number) => byKey.get(`${q},${r}`);

  return {
    edgeKm,
    spacingKm,
    cellAreaKm2: (3 * SQRT3 * edgeKm * edgeKm) / 2,
    cells,
    boundary,
    project,
    unproject,
    neighbours(index) {
      const c = cells[index];
      const out: number[] = [];
      for (const [dq, dr] of DIRS) {
        const n = lookup(c.q + dq, c.r + dr);
        if (n !== undefined) out.push(n);
      }
      return out;
    },
    within(x, y, radiusKm) {
      const [q0, r0] = toQR(x, y);
      const k = Math.ceil(radiusKm / spacingKm) + 1;
      const out: number[] = [];
      for (let dq = -k; dq <= k; dq++) {
        for (let dr = Math.max(-k, -dq - k); dr <= Math.min(k, -dq + k); dr++) {
          const n = lookup(q0 + dq, r0 + dr);
          if (n === undefined) continue;
          const c = cells[n];
          if (Math.hypot(c.x - x, c.y - y) <= radiusKm + 1e-9) out.push(n);
        }
      }
      return out;
    },
    cellAt(x, y) {
      const [q, r] = toQR(x, y);
      return lookup(q, r);
    },
    corners(c) {
      const out: Point[] = [];
      for (let i = 0; i < 6; i++) {
        const a = (Math.PI / 180) * (60 * i - 30);
        out.push({ x: c.x + edgeKm * Math.cos(a), y: c.y + edgeKm * Math.sin(a) });
      }
      return out;
    },
  };
}
