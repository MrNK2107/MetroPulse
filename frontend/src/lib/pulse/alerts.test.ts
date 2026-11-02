import { getCity, listCities } from "./geo";
import { buildCityModel } from "./model";
import { detectIncidents, median4, robustStats, Z_THRESHOLD } from "./alerts";
import { mulberry32 } from "./model";

describe("robust statistics", () => {
  it("returns the median and MAD", () => {
    expect(robustStats([10, 12, 11, 50])).toEqual({ median: 11.5, mad: 1 });
  });

  it("median4 agrees with the sorted median for any order", () => {
    const r = mulberry32(7);
    for (let k = 0; k < 2000; k++) {
      const v = [r(), r(), r(), r()].map((x) => Math.round(x * 20));
      expect(median4(v[0], v[1], v[2], v[3])).toBeCloseTo(robustStats(v).median, 10);
    }
  });
});

describe("incident detection", () => {
  const model = buildCityModel(getCity("chennai")!);
  const incidents = detectIncidents(model);

  it("finds every scripted incident in the sample week", () => {
    expect(model.scripted.length).toBeGreaterThanOrEqual(3);
    for (const s of model.scripted) {
      const hit = incidents.find(
        (i) => i.kind === s.kind && i.startHour <= s.peakHour && i.endHour >= s.peakHour
      );
      expect(hit).toBeDefined();
    }
  });

  it("raises few false alarms on ordinary noise", () => {
    expect(incidents.length).toBeLessThanOrEqual(model.scripted.length + 2);
  });

  it("explains each incident in a sentence with a rule trace", () => {
    for (const i of incidents) {
      expect(i.headline.length).toBeGreaterThan(10);
      expect(i.explanation).toMatch(/\d/);
      expect(i.likelyCause.length).toBeGreaterThan(5);
      expect(i.whatToCheck.length).toBeGreaterThan(5);
      expect(i.ruleTrace.length).toBeGreaterThanOrEqual(3);
      expect(i.cells.length).toBeGreaterThan(0);
    }
  });

  it("sorts incidents by severity", () => {
    for (let k = 1; k < incidents.length; k++) {
      expect(Math.abs(incidents[k - 1].excessTrips)).toBeGreaterThanOrEqual(Math.abs(incidents[k].excessTrips));
    }
  });

  it("keeps the peak ratio finite on hexagons with an empty baseline", () => {
    const zero = new Float32Array(model.thisWeek.length);
    const spike = new Float32Array(model.thisWeek.length);
    const H = 168;
    const c = model.grid.cells.length >> 1;
    for (const cell of [c, ...model.grid.neighbours(c)]) for (let h = 30; h < 33; h++) spike[cell * H + h] = 50;
    const found = detectIncidents({ ...model, baselineWeeks: [zero, zero, zero, zero], thisWeek: spike });
    expect(found).toHaveLength(1);
    expect(found[0].kind).toBe("surge");
    expect(Number.isFinite(found[0].peakRatio)).toBe(true);
    expect(found[0].explanation).not.toMatch(/Infinity|NaN/);
  });

  it("does not flag a change below the relative threshold even when z is large", () => {
    // a steady baseline makes MAD ~0, so z is huge; a 20% rise must still not count
    const base = model.baselineMean;
    const up = base.map((v) => v * 1.2);
    expect(Z_THRESHOLD).toBeGreaterThan(0);
    expect(detectIncidents({ ...model, baselineWeeks: [base, base, base, base], thisWeek: up })).toHaveLength(0);
  });

  it("finds nothing when the current week equals the baseline", () => {
    const quiet = { ...model, thisWeek: model.baselineMean };
    expect(detectIncidents(quiet)).toHaveLength(0);
  });
});

describe("every sample city", () => {
  it.each(listCities().map((c) => c.id))("%s: finds its scripted incidents without a flood of false alarms", (id) => {
    const m = buildCityModel(getCity(id)!);
    const found = detectIncidents(m);
    for (const s of m.scripted) {
      expect(found.some((i) => i.kind === s.kind && i.startHour <= s.peakHour && i.endHour >= s.peakHour)).toBe(true);
    }
    expect(found.length).toBeLessThanOrEqual(m.scripted.length + 2);
  });
});
