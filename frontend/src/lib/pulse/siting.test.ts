import { getCity } from "./geo";
import { buildCityModel } from "./model";
import { catchment, MODES, scoreSite, suggestSites, existingCoverage, transitDesertShare, walkCoverage } from "./siting";

const model = buildCityModel(getCity("chennai")!);

describe("station siting", () => {
  it("defines metro, BRT and feeder modes with walk bands", () => {
    expect(MODES.metro.walkKm).toBe(0.8);
    expect(MODES.brt.walkKm).toBeLessThan(MODES.metro.walkKm);
    expect(Object.keys(MODES)).toEqual(["metro", "brt", "feeder"]);
  });

  it("scores a site with catchment, boardings, peak hour and a 0-100 score", () => {
    const busiest = model.grid.cells[model.rankCellsByDailyTrips()[0]];
    const r = scoreSite(model, { x: busiest.x, y: busiest.y }, "metro");
    expect(r.walkCells.length).toBeGreaterThan(0);
    expect(r.feederCells.length).toBeGreaterThan(r.walkCells.length);
    expect(r.residents).toBeGreaterThan(0);
    expect(r.jobs).toBeGreaterThan(0);
    expect(r.dailyBoardings).toBeGreaterThan(0);
    expect(r.newShare).toBeGreaterThanOrEqual(0);
    expect(r.newShare).toBeLessThanOrEqual(1);
    expect(r.score).toBeGreaterThanOrEqual(0);
    expect(r.score).toBeLessThanOrEqual(100);
    expect(r.peakHour).toBeGreaterThanOrEqual(0);
    expect(r.peakHour).toBeLessThan(24);
    expect(r.formula).toContain("60");
  });

  it("scores a busy core above an empty edge", () => {
    const order = model.rankCellsByDailyTrips();
    const busy = model.grid.cells[order[0]];
    const quiet = model.grid.cells[order[order.length - 1]];
    expect(scoreSite(model, busy, "metro").score).toBeGreaterThan(scoreSite(model, quiet, "metro").score);
  });

  it("counts demand already served by existing hubs as cannibalised", () => {
    const covered = existingCoverage(model);
    const hub = model.city.anchors.find((a) => a.type === "transport")!;
    const p = model.grid.project(hub.lat, hub.lng);
    const r = scoreSite(model, p, "metro", covered);
    const uncovered = scoreSite(model, p, "metro");
    expect(uncovered.newShare).toBe(1);
    // a station on top of the hub: its whole walk band is already served
    expect(r.newShare).toBeLessThan(0.7);
    expect(r.newBoardings).toBeLessThan(uncovered.newBoardings);
    expect(r.dailyBoardings).toBeCloseTo(uncovered.dailyBoardings, 6);
  });

  it("suggests three distinct sites whose coverage does not overlap much", () => {
    const picks = suggestSites(model, "metro", 3);
    expect(picks).toHaveLength(3);
    const ids = new Set(picks.map((p) => p.cell));
    expect(ids.size).toBe(3);
    // greedy: each later pick adds less new demand than the first
    expect(picks[0].result.newBoardings).toBeGreaterThanOrEqual(picks[2].result.newBoardings);
    for (let a = 0; a < 3; a++)
      for (let b = a + 1; b < 3; b++) {
        const pa = model.grid.cells[picks[a].cell];
        const pb = model.grid.cells[picks[b].cell];
        expect(Math.hypot(pa.x - pb.x, pa.y - pb.y)).toBeGreaterThan(MODES.metro.walkKm);
      }
  });
});

describe("transit-desert share", () => {
  it("is the share of residents outside every existing hub's walk band", () => {
    const share = transitDesertShare(model);
    expect(share).toBeGreaterThan(0);
    expect(share).toBeLessThan(1);
    const covered = existingCoverage(model);
    let inside = 0;
    covered.forEach((w, c) => (inside += w * model.residents[c]));
    expect(share).toBeCloseTo(1 - inside / model.city.population, 3);
  });
});

describe("walk-band coverage", () => {
  it("is the residents' share within walking distance of hubs, and grows with the suggested sites", () => {
    const today = walkCoverage(model);
    expect(today).toBeCloseTo(1 - transitDesertShare(model), 6);
    const picks = suggestSites(model, "metro", 3);
    const after = walkCoverage(model, picks.map((p) => p.result));
    expect(after).toBeGreaterThan(today);
    // adding the same sites again changes nothing (no double counting)
    expect(walkCoverage(model, [...picks, ...picks].map((p) => p.result))).toBeCloseTo(after, 9);
    expect(after).toBeLessThanOrEqual(1);
  });
});

describe("catchment geometry", () => {
  it("does not depend on where inside a hexagon the pin lands", () => {
    // Before area weighting, a pin on a cell centre got a 1-hexagon walk band
    // (neighbours are 0.92 km away, outside 0.8 km) while a pin between cells got 3.
    const c = model.grid.cells[model.rankCellsByDailyTrips()[10]];
    const centre = scoreSite(model, c, "metro").dailyBoardings;
    const offset = scoreSite(model, { x: c.x + model.grid.edgeKm * 0.5, y: c.y + model.grid.edgeKm * 0.3 }, "metro").dailyBoardings;
    expect(offset / centre).toBeGreaterThan(0.85);
    expect(offset / centre).toBeLessThan(1.15);
  });

  it("weights each hexagon by the share of its area inside the circle", () => {
    const c = model.grid.cells[Math.floor(model.grid.cells.length / 2)];
    const big = catchment(model.grid, c, 0.01);
    expect(big.cells).toEqual([c.index]);
    expect(big.weights[0]).toBeLessThan(0.2);
    // the most interior hexagon, so a 5 km circle is not clipped by the boundary
    const g = model.grid;
    const inner = g.cells.reduce((b, x) => (g.within(x.x, x.y, 6).length > g.within(b.x, b.y, 6).length ? x : b));
    const all = catchment(g, inner, 5);
    const area = all.weights.reduce((a, w) => a + w, 0) * g.cellAreaKm2;
    // pi * 25 = 78.5 km2, to within sampling error
    expect(area).toBeGreaterThan(78.5 * 0.9);
    expect(area).toBeLessThan(78.5 * 1.1);
    const walk = catchment(model.grid, c, MODES.metro.walkKm);
    const walkArea = walk.weights.reduce((a, w) => a + w, 0) * model.grid.cellAreaKm2;
    expect(walkArea).toBeGreaterThan(Math.PI * 0.64 * 0.8);
    expect(walkArea).toBeLessThan(Math.PI * 0.64 * 1.2);
  });
});
