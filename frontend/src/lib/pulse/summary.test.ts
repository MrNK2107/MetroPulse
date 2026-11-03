import { getCity } from "./geo";
import { buildCityModel } from "./model";
import { citySummary } from "./summary";

describe("citySummary", () => {
  const model = buildCityModel(getCity("chennai")!);
  const s = citySummary(model);

  it("carries the identity and headline numbers", () => {
    expect(s.id).toBe("chennai");
    expect(s.name).toBe("Chennai");
    expect(s.state).toBe("Tamil Nadu");
    expect(s.population).toBe(model.city.population);
    expect(s.dailyTrips).toBeGreaterThan(1e6);
    expect(s.peakHour).toBeGreaterThanOrEqual(0);
    expect(s.peakHour).toBeLessThan(24);
    expect(s.coverageAfter).toBeGreaterThan(s.coverageNow);
  });

  it("summarises incidents and the three suggested metro sites", () => {
    expect(s.incidents.total).toBe(s.incidents.surges + s.incidents.drops);
    expect(s.topIncidents.length).toBeLessThanOrEqual(3);
    expect(s.topIncidents.length).toBeGreaterThan(0);
    expect(s.suggested).toHaveLength(3);
    for (const site of s.suggested) {
      expect(site.name).toBeTruthy();
      expect(site.boardings).toBeGreaterThan(0);
      expect(Math.abs(site.lat - 13.08)).toBeLessThan(0.5);
      expect(Math.abs(site.lng - 80.27)).toBeLessThan(0.5);
      expect(site.score).toBeGreaterThanOrEqual(0);
    }
  });

  it("writes the headline and lede the briefing uses", () => {
    expect(s.headline).toMatch(/^Chennai: \d+ incidents this week, and the next station belongs /);
    expect(s.headline).not.toMatch(/near \d/);
    expect(s.lede).toMatch(/residents make about/);
    expect(s.lede).toMatch(/would raise that to/);
  });
});
