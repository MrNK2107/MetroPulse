import { parseZonesCsv } from "./zones";

describe("parseZonesCsv", () => {
  it("reads zone, lat, lng, residents and jobs with header synonyms", () => {
    const r = parseZonesCsv("zone,latitude,longitude,population,employment\nTAZ 1,13.08,80.27,12000,30000\nTAZ 2,13.05,80.25,25000,4000\n");
    expect(r.ok && r.value).toEqual([
      { name: "TAZ 1", lat: 13.08, lng: 80.27, residents: 12000, jobs: 30000 },
      { name: "TAZ 2", lat: 13.05, lng: 80.25, residents: 25000, jobs: 4000 },
    ]);
    expect(r.ok && r.report[0]).toMatch(/2 zones .* 37,000 residents .* 34,000 jobs/);
  });

  it("keeps an optional radius and defaults missing jobs to 0", () => {
    const r = parseZonesCsv("name,lat,lng,residents,radius_km\nA,13.08,80.27,100,1.5\n");
    expect(r.ok && r.value).toEqual([{ name: "A", lat: 13.08, lng: 80.27, residents: 100, jobs: 0, radiusKm: 1.5 }]);
  });

  it("fails without a residents column and skips bad rows with a report", () => {
    expect(parseZonesCsv("name,lat,lng\nA,13,80\n").ok).toBe(false);
    const r = parseZonesCsv("name,lat,lng,residents\nA,13.08,80.27,abc\nB,13.05,80.25,10\n");
    expect(r.ok && r.value).toHaveLength(1);
    expect(r.ok && r.report.join(" ")).toMatch(/1 row.*skipped/);
  });
});
