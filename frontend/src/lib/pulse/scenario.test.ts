import { getCity } from "./geo";
import { buildCityModel } from "./model";
import { existingCoverage, scoreSite, suggestSites } from "./siting";
import {
  DEFAULT_COSTS,
  decodeScenario,
  encodeScenario,
  evaluateScenario,
  newScenarioId,
  Scenario,
  scenarioFromSuggestions,
  SPACING_KM,
} from "./scenario";

const city = getCity("chennai")!;
const model = buildCityModel(city);
const base = (stations: Scenario["stations"], extra: Partial<Scenario> = {}): Scenario => ({
  id: "abcd2345",
  cityId: "chennai",
  name: "Test line",
  mode: "metro",
  alignment: "elevated",
  stations,
  createdAt: "2026-11-03T00:00:00.000Z",
  updatedAt: "2026-11-03T00:00:00.000Z",
  ...extra,
});

// Two points about 1.2 km apart near T Nagar, [lat, lng]
const A = { lat: 13.0418, lng: 80.2341 };
const B = { lat: 13.0418, lng: 80.2452 };
const kmAB = model.grid.project(A.lat, A.lng);
const kmB = model.grid.project(B.lat, B.lng);
const distAB = Math.hypot(kmAB.x - kmB.x, kmAB.y - kmB.y);

describe("evaluateScenario", () => {
  it("sums length, costs the line from the table and scores spacing inside the band", () => {
    const r = evaluateScenario(model, base([A, B]));
    expect(r.stations).toHaveLength(2);
    expect(r.lengthKm).toBeCloseTo(distAB, 6);
    expect(r.costCr).toBeCloseTo(distAB * DEFAULT_COSTS.perKmCr.elevated + 2 * DEFAULT_COSTS.perStationCr.elevated, 6);
    expect(r.spacingCompliance).toBe(1);
    expect(r.stations[0].spacingKmToNext).toBeCloseTo(distAB, 6);
    expect(r.stations[0].spacingWarning).toBeUndefined();
    expect(r.stations[1].spacingKmToNext).toBeUndefined();
    expect(r.costPerBoardingLakh).toBeCloseTo((r.costCr * 100) / r.boardings, 6);
    expect(r.formula).toContain("50 x min(1,");
    expect(r.costFormula).toContain("250");
  });

  it("warns when two stations are closer than the band", () => {
    const close = { lat: 13.0418, lng: 80.2369 }; // ~0.3 km east of A
    const r = evaluateScenario(model, base([A, close]));
    expect(r.spacingCompliance).toBe(0);
    expect(r.stations[0].spacingWarning).toMatch(/^0\.3 km to the next station, below the 0\.8 km band/);
    expect(SPACING_KM.metro).toEqual([0.8, 2.0]);
  });

  it("counts the second station's boardings net of the first (cannibalisation)", () => {
    const alone = scoreSite(model, kmB, "metro", existingCoverage(model));
    const r = evaluateScenario(model, base([A, B]));
    expect(r.stations[1].newBoardings).toBeLessThan(alone.newBoardings);
    expect(r.boardings).toBeGreaterThan(0);
    expect(r.newShare).toBeGreaterThan(0);
    expect(r.newShare).toBeLessThanOrEqual(1);
    expect(r.coverageAfter).toBeGreaterThan(r.coverageNow);
    expect(r.score).toBeGreaterThanOrEqual(0);
    expect(r.score).toBeLessThanOrEqual(100);
  });

  it("uses the scenario's own cost table when given", () => {
    const costs = { perKmCr: { elevated: 100, underground: 600, "at-grade": 120 }, perStationCr: { elevated: 10, underground: 250, "at-grade": 20 } };
    const r = evaluateScenario(model, base([A, B], { costs }));
    expect(r.costCr).toBeCloseTo(distAB * 100 + 20, 6);
  });
});

describe("scenario URL encoding", () => {
  it("round-trips mode, alignment and coordinates to four decimals", () => {
    const s = base([A, B], { mode: "brt", alignment: "underground" });
    const enc = encodeScenario(s);
    expect(enc).toBe("b.u.13.0418,80.2341;13.0418,80.2452");
    const back = decodeScenario(enc, "chennai");
    expect(back?.mode).toBe("brt");
    expect(back?.alignment).toBe("underground");
    expect(back?.stations).toEqual([A, B]);
    expect(back?.cityId).toBe("chennai");
    expect(back?.name).toBe("Shared line");
  });

  it("returns null for malformed text, an unknown city or a far-away coordinate", () => {
    expect(decodeScenario("x", "chennai")).toBeNull();
    expect(decodeScenario("m.e.", "chennai")).toBeNull();
    expect(decodeScenario("m.e.13.0418,abc", "chennai")).toBeNull();
    expect(decodeScenario("m.e.13.0418,80.2341", "atlantis")).toBeNull();
    expect(decodeScenario("m.e.19.0760,72.8777", "chennai")).toBeNull(); // Mumbai
  });
});

describe("scenario helpers", () => {
  it("makes 8-character ids from the unambiguous alphabet", () => {
    const id = newScenarioId();
    expect(id).toMatch(/^[abcdefghjkmnpqrstuvwxyz23456789]{8}$/);
    expect(newScenarioId()).not.toBe(id);
  });

  it("turns greedy suggestions into a scenario in pick order", () => {
    const picks = suggestSites(model, "metro", 3);
    const s = scenarioFromSuggestions(model, "metro", picks);
    expect(s.stations).toHaveLength(3);
    expect(s.mode).toBe("metro");
    expect(s.name).toBe("Suggested metro line");
    const first = model.grid.unproject(model.grid.cells[picks[0].cell]);
    expect(s.stations[0].lat).toBeCloseTo(first.lat, 4);
  });
});
