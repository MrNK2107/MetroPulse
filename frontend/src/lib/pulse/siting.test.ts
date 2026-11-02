import { getCity } from "./geo";
import { buildCityModel } from "./model";
import { MODES, scoreSite, suggestSites, existingCoverage } from "./siting";

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
    // the whole walk band is already served, so at least that share is cannibalised
    const walkShare =
      r.walkCells.reduce((a, c) => a + model.dailyTrips[c] * MODES.metro.walkCapture, 0) / r.dailyBoardings;
    expect(walkShare).toBeGreaterThan(0.3);
    expect(r.newShare).toBeLessThanOrEqual(1 - walkShare + 1e-6);
    expect(r.newShare).toBeLessThan(0.6);
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
