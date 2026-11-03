import { parseBoundaryGeoJson, ringAreaKm2 } from "./geojson";

const CHENNAI: [number, number] = [13.0827, 80.2707];
// a square around a centre, [lng, lat]
const sq = (cx: number, cy: number, d: number): [number, number][] => [
  [cx - d, cy - d],
  [cx + d, cy - d],
  [cx + d, cy + d],
  [cx - d, cy + d],
  [cx - d, cy - d],
];
const big = sq(80.27, 13.08, 0.2);
const small = sq(80.4, 13.2, 0.02);

describe("parseBoundaryGeoJson", () => {
  it("takes the larger polygon of a FeatureCollection", () => {
    const fc = {
      type: "FeatureCollection",
      features: [
        { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [small] } },
        { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [big] } },
      ],
    };
    const r = parseBoundaryGeoJson(JSON.stringify(fc), CHENNAI);
    expect(r.ok && r.value).toEqual(big);
    expect(r.ok && r.report.join(" ")).toMatch(/km²/);
  });

  it("takes the largest part of a MultiPolygon and drops holes", () => {
    const hole = sq(80.27, 13.08, 0.05);
    const mp = { type: "MultiPolygon", coordinates: [[small], [big, hole]] };
    const r = parseBoundaryGeoJson(JSON.stringify(mp), CHENNAI);
    expect(r.ok && r.value).toEqual(big);
  });

  it("closes an unclosed ring", () => {
    const open = big.slice(0, 4);
    const r = parseBoundaryGeoJson(JSON.stringify({ type: "Polygon", coordinates: [open] }), CHENNAI);
    expect(r.ok && r.value).toEqual(big);
  });

  it("rejects a ring with fewer than 3 distinct vertices", () => {
    const r = parseBoundaryGeoJson(JSON.stringify({ type: "Polygon", coordinates: [big.slice(0, 2)] }), CHENNAI);
    expect(r.ok).toBe(false);
  });

  it("rejects a boundary far from the city and says how far", () => {
    const mumbai = sq(72.88, 19.08, 0.2);
    const r = parseBoundaryGeoJson(JSON.stringify({ type: "Polygon", coordinates: [mumbai] }), CHENNAI);
    expect(r).toEqual({ ok: false, error: expect.stringMatching(/about \d+ km from/) });
  });

  it("rejects coordinates out of range and invalid JSON", () => {
    const bad = sq(200, 13.08, 0.2);
    expect(parseBoundaryGeoJson(JSON.stringify({ type: "Polygon", coordinates: [bad] }), CHENNAI).ok).toBe(false);
    expect(parseBoundaryGeoJson("{not json", CHENNAI).ok).toBe(false);
  });
});

describe("ringAreaKm2", () => {
  it("measures a 0.4 x 0.4 degree square near 13 N at roughly 1,900 km²", () => {
    const a = ringAreaKm2(big);
    expect(a).toBeGreaterThan(1800);
    expect(a).toBeLessThan(2000);
  });
});
