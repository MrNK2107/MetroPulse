import { getCity, listCities } from "./geo";
import { buildCityModel } from "./model";
import { detectIncidents, robustStats } from "./alerts";

describe("robust statistics", () => {
  it("returns the median and MAD", () => {
    expect(robustStats([10, 12, 11, 50])).toEqual({ median: 11.5, mad: 1 });
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
