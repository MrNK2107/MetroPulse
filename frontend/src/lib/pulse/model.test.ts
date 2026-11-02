import { buildHexGrid, getCity, listCities, hexDistanceKm } from "./geo";
import { buildCityModel, HOURS_PER_WEEK, dayHourLabel } from "./model";

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
