import { buildHexGrid, getCity, listCities, hexDistanceKm } from "./geo";
import { buildCityModel, getCityModel, HOURS_PER_WEEK, dayHourLabel, modelCacheSize } from "./model";

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

describe("model cache", () => {
  it("keeps at most 8 data-keyed models", () => {
    const city = getCity("chennai")!;
    for (let k = 0; k < 10; k++) {
      getCityModel(city, {
        version: 1,
        cityId: "chennai",
        hubs: { source: `s${k}.csv`, stations: [{ name: `S${k}`, lat: 13.0827, lng: 80.2707 + k * 0.001, mode: "metro" }] },
        loadedAt: "2026-11-03T00:00:00.000Z",
      });
    }
    expect(modelCacheSize()).toBeLessThanOrEqual(8);
  });
});

describe("city model with the user's zones", () => {
  const city = getCity("chennai")!;
  const zones = [
    { name: "Core", lat: 13.0827, lng: 80.2707, residents: 400000, jobs: 600000 },
    { name: "South", lat: 12.99, lng: 80.22, residents: 300000, jobs: 50000 },
  ];
  const data = { version: 1 as const, cityId: "chennai", zones: { source: "zones.csv", rows: zones }, loadedAt: "2026-11-03T00:00:00.000Z" };

  it("spreads each zone's residents and jobs over nearby hexagons and keeps the totals", () => {
    const m = buildCityModel(city, data);
    expect(Array.from(m.residents).reduce((a, b) => a + b, 0)).toBeCloseTo(700000, -1);
    expect(Array.from(m.jobs).reduce((a, b) => a + b, 0)).toBeCloseTo(650000, -1);
    const core = m.grid.cellAt(m.grid.project(13.0827, 80.2707).x, m.grid.project(13.0827, 80.2707).y)!;
    const south = m.grid.cellAt(m.grid.project(12.99, 80.22).x, m.grid.project(12.99, 80.22).y)!;
    expect(m.jobs[core]).toBeGreaterThan(m.jobs[south] * 3);
    expect(m.residents[south]).toBeGreaterThan(m.residents[core] * 0.5);
    expect(m.city.population).toBe(700000);
    expect(m.dailyTrips.reduce((a, b) => a + b, 0)).toBeGreaterThan(0);
  });

  it("leaves a cell far from every zone empty", () => {
    const m = buildCityModel(city, data);
    const far = m.grid.cells.reduce((best, c) => {
      const d = Math.min(...zones.map((z) => Math.hypot(c.x - m.grid.project(z.lat, z.lng).x, c.y - m.grid.project(z.lat, z.lng).y)));
      return d > best.d ? { d, c } : best;
    }, { d: -1, c: m.grid.cells[0] });
    expect(m.residents[far.c.index]).toBe(0);
  });
});

describe("city model with an observed hourly profile", () => {
  const city = getCity("chennai")!;
  const hourly = Array(24).fill(0.01);
  hourly[20] = 1 - 0.23; // a sharp 20:00 peak; the rest flat
  const data = { version: 1 as const, cityId: "chennai", counts: { source: "c.csv", rows: [{ station: "X", dailyBoardings: 1 }], hourly }, loadedAt: "2026-11-03T00:00:00.000Z" };

  it("reshapes weekday hours to the observed profile and keeps each cell's daily total", () => {
    const base = buildCityModel(city);
    const m = buildCityModel(city, data);
    const tue = m.cityHourly(m.baselineMean).slice(24, 48);
    expect(tue.indexOf(Math.max(...tue))).toBe(20);
    const c = m.rankCellsByDailyTrips()[0];
    const day = (model: typeof m, cell: number) => Array.from({ length: 24 }, (_, h) => model.baselineMean[cell * 168 + 24 + h]).reduce((a, b) => a + b, 0);
    expect(day(m, c)).toBeCloseTo(day(base, c), 1);
    // weekends keep the model's profile
    const sun = m.cityHourly(m.baselineMean).slice(144, 168);
    expect(sun.indexOf(Math.max(...sun))).not.toBe(20);
    expect(Array.from(m.dailyTrips).reduce((a, b) => a + b, 0)).toBeCloseTo(Array.from(base.dailyTrips).reduce((a, b) => a + b, 0), -2);
  });
});
