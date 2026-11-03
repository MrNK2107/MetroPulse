import { buildHexGrid, getCity, listCities, hexDistanceKm } from "./geo";
import { buildCityModel, getCityModel, HOURS_PER_WEEK, dayHourLabel } from "./model";

describe("sample city catalogue", () => {
  it("ships all 30 configured cities", () => {
    expect(listCities()).toHaveLength(30);
    expect(getCity("chennai")?.name).toBe("Chennai");
    expect(getCity("atlantis")).toBeUndefined();
  });
});

describe("hex grid", () => {
  const city = getCity("chennai")!;
  const grid = buildHexGrid(city);

  it("covers the boundary with cells of about 0.74 km2", () => {
    expect(grid.cellAreaKm2).toBeCloseTo(0.74, 1);
    expect(grid.cells.length).toBeGreaterThan(500);
  });

  it("gives every cell up to six adjacent neighbours one spacing apart", () => {
    const c = grid.cells[Math.floor(grid.cells.length / 2)];
    const ns = grid.neighbours(c.index);
    expect(ns.length).toBeGreaterThan(0);
    expect(ns.length).toBeLessThanOrEqual(6);
    for (const n of ns) {
      expect(hexDistanceKm(c, grid.cells[n])).toBeCloseTo(grid.spacingKm, 5);
    }
  });

  it("finds cells within a radius", () => {
    const c = grid.cells[Math.floor(grid.cells.length / 2)];
    const near = grid.within(c.x, c.y, 1.0);
    expect(near).toContain(c.index);
    for (const i of near) expect(hexDistanceKm(c, grid.cells[i])).toBeLessThanOrEqual(1.0);
  });
});

describe("city model", () => {
  const model = buildCityModel(getCity("chennai")!);

  it("is deterministic for a city", () => {
    const again = buildCityModel(getCity("chennai")!);
    expect(Array.from(again.thisWeek.slice(0, 500))).toEqual(Array.from(model.thisWeek.slice(0, 500)));
  });

  it("allocates the published population across cells", () => {
    const total = model.residents.reduce((a, b) => a + b, 0);
    expect(total / model.city.population).toBeCloseTo(1, 2);
    expect(model.jobs.reduce((a, b) => a + b, 0)).toBeGreaterThan(0);
  });

  it("has a 168-hour week with a weekday morning peak above the small hours", () => {
    expect(HOURS_PER_WEEK).toBe(168);
    const total = model.cityHourly(model.baselineMean);
    expect(total).toHaveLength(168);
    // Tuesday 09:00 vs Tuesday 03:00
    expect(total[24 + 9]).toBeGreaterThan(total[24 + 3] * 3);
    // Sunday morning is quieter than Tuesday morning
    expect(total[6 * 24 + 9]).toBeLessThan(total[24 + 9]);
  });

  it("keeps four baseline weeks plus the current week", () => {
    expect(model.baselineWeeks).toHaveLength(4);
    expect(model.thisWeek.length).toBe(model.grid.cells.length * 168);
  });

  it("labels hours", () => {
    expect(dayHourLabel(0)).toBe("Mon 00:00");
    expect(dayHourLabel(24 * 4 + 19)).toBe("Fri 19:00");
  });
});

describe("city model with the user's own data", () => {
  const city = getCity("chennai")!;
  const ring: [number, number][] = [
    [80.2, 13.0],
    [80.34, 13.0],
    [80.34, 13.16],
    [80.2, 13.16],
    [80.2, 13.0],
  ];
  const stations = [
    { name: "Central", lat: 13.0827, lng: 80.2707, mode: "metro" as const },
    { name: "Mylapore Bus", lat: 13.03, lng: 80.27, mode: "feeder" as const },
  ];
  const data = { version: 1 as const, cityId: "chennai", boundary: { source: "b.geojson", ring }, hubs: { source: "s.csv", stations }, loadedAt: "2026-11-03T00:00:00.000Z" };

  it("keeps the 1.x figures when no data is given", () => {
    const m = buildCityModel(city);
    expect(m.grid.cells.length).toBe(622);
    expect(Array.from(m.dailyTrips).reduce((a, b) => a + b, 0)).toBeCloseTo(28599999.983398438, 3);
    expect(m.thisWeek[0]).toBeCloseTo(138.7960205078125, 6);
    expect(m.hubs.map((h) => h.mode)).toEqual(m.city.anchors.filter((a) => a.type === "transport").map(() => "metro"));
    expect(m.data).toBeNull();
  });

  it("builds the grid on the user's boundary and lists their stations as hubs", () => {
    const m = buildCityModel(city, data);
    expect(m.grid.cells.length).not.toBe(622);
    expect(m.grid.cells.length).toBeGreaterThan(50);
    expect(m.hubs).toEqual(stations);
    expect(m.data).toBe(data);
    expect(m.nearestAnchor(m.grid.project(13.0827, 80.2707)).anchor.name).toBe("Central");
  });

  it("memoises per city and per data key", () => {
    expect(getCityModel(city)).toBe(getCityModel(city));
    expect(getCityModel(city, data)).toBe(getCityModel(city, data));
    expect(getCityModel(city, data)).not.toBe(getCityModel(city));
  });
});
