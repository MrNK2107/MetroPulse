import { buildHexGrid, getCity } from "./geo";
import citiesJson from "@/data/cities.json";

describe("buildHexGrid projection", () => {
  // Node (server render) and the browser can disagree on the last bit of Math.cos,
  // which made anchor and outline coordinates differ between the server HTML and
  // the client and triggered hydration warnings (Guwahati, Lucknow, Vadodara).
  // The east-west scale is rounded to 1e-9 km per degree, so every projected
  // x is a plain product of identical doubles on both sides.
  it("uses an east-west scale rounded to 1e-9 km per degree in every city", () => {
    for (const c of citiesJson as { id: string }[]) {
      const city = getCity(c.id)!;
      const grid = buildHexGrid(city);
      const kx = grid.project(city.center[0], city.center[1] + 1).x;
      expect(Math.abs(kx * 1e9 - Math.round(kx * 1e9))).toBeLessThan(1e-3);
    }
  });
});

describe("hex grid on a very detailed ring", () => {
  it("builds without a stack overflow on a 200,000-vertex boundary", () => {
    const city = getCity("chennai")!;
    const ring: [number, number][] = [];
    for (let i = 0; i < 200000; i++) {
      const t = (2 * Math.PI * i) / 200000;
      ring.push([80.2707 + (12 * Math.cos(t)) / 108.4, 13.0827 + (12 * Math.sin(t)) / 110.57]);
    }
    ring.push(ring[0]);
    const grid = buildHexGrid({ ...city, boundary: ring });
    expect(grid.cells.length).toBeGreaterThan(400);
  });
});
