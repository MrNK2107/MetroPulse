import { getCity } from "./geo";
import { buildCityModel } from "./model";
import { calibrate, UNCALIBRATED } from "./calibrate";
import { scoreSite } from "./siting";

const city = getCity("chennai")!;
const stations = [
  { name: "Central", lat: 13.0827, lng: 80.2707, mode: "metro" as const },
  { name: "Egmore", lat: 13.0732, lng: 80.2609, mode: "metro" as const },
  { name: "T Nagar", lat: 13.0418, lng: 80.2341, mode: "metro" as const },
  { name: "Guindy", lat: 13.0067, lng: 80.2206, mode: "metro" as const },
];
const withHubs = (n: number) =>
  buildCityModel(city, { version: 1, cityId: "chennai", hubs: { source: "s.csv", stations: stations.slice(0, n) }, loadedAt: "2026-11-03T00:00:00.000Z" });

/** Modelled boardings at each hub with no calibration and no cannibalisation. */
const modelled = (m: ReturnType<typeof withHubs>) =>
  m.hubs.map((h) => scoreSite(m, m.grid.project(h.lat, h.lng), h.mode).dailyBoardings);

describe("calibrate", () => {
  it("takes the median observed/modelled ratio per mode over at least 3 matched stations", () => {
    const m = withHubs(4);
    const rows = m.hubs.map((h, k) => ({ station: h.name, dailyBoardings: modelled(m)[k] * 0.5 }));
    const c = calibrate(m, rows);
    expect(c.factor.metro).toBeCloseTo(0.5, 6);
    expect(c.iqr.metro).toBeCloseTo(0, 6);
    expect(c.stations.metro).toBe(4);
    expect(c.matched).toHaveLength(4);
    expect(c.unmatched).toEqual([]);
    expect(c.factor.brt).toBe(1);
  });

  it("leaves a mode uncalibrated with fewer than 3 matches but still reports them", () => {
    const m = withHubs(2);
    const rows = [
      { station: "Central Metro Station", dailyBoardings: 10 },
      { station: "egmore", dailyBoardings: 20 },
      { station: "Nowhere", dailyBoardings: 5 },
    ];
    const c = calibrate(m, rows);
    expect(c.factor.metro).toBe(1);
    expect(c.stations.metro).toBe(2);
    expect(c.matched.map((x) => x.station)).toEqual(["Central", "Egmore"]);
    expect(c.unmatched).toEqual(["Nowhere"]);
  });

  it("reports the spread as IQR over median", () => {
    const m = withHubs(4);
    const ratios = [0.5, 1, 1.5, 2];
    const rows = m.hubs.map((h, k) => ({ station: h.name, dailyBoardings: modelled(m)[k] * ratios[k] }));
    const c = calibrate(m, rows);
    expect(c.factor.metro).toBeCloseTo(1.25, 6);
    expect(c.iqr.metro).toBeGreaterThan(0.5);
  });

  it("has an uncalibrated default", () => {
    expect(UNCALIBRATED.factor).toEqual({ metro: 1, brt: 1, feeder: 1 });
    expect(UNCALIBRATED.stations.metro).toBe(0);
  });
});

describe("scoreSite with a calibration", () => {
  it("scales boardings and says so in the formula", () => {
    const m = withHubs(4);
    const site = m.grid.cells[m.rankCellsByDailyTrips()[0]];
    const raw = scoreSite(m, site, "metro");
    const cal = { ...UNCALIBRATED, factor: { metro: 0.5, brt: 1, feeder: 1 }, stations: { metro: 4, brt: 0, feeder: 0 }, iqr: { metro: 0.18, brt: 0, feeder: 0 } };
    const r = scoreSite(m, site, "metro", undefined, cal);
    expect(r.dailyBoardings).toBeCloseTo(raw.dailyBoardings * 0.5, 3);
    expect(r.hourly[9]).toBeCloseTo(raw.hourly[9] * 0.5, 3);
    expect(r.formula).toContain("× 0.50 (calibrated on 4 stations, IQR ±18%)");
    expect(scoreSite(m, site, "brt", undefined, cal).formula).not.toContain("calibrated");
  });

  it("is computed on the model when counts and hubs are loaded", () => {
    const m = withHubs(4);
    const rows = m.hubs.map((h, k) => ({ station: h.name, dailyBoardings: modelled(m)[k] * 0.5 }));
    const withCounts = buildCityModel(city, { ...m.data!, counts: { source: "c.csv", rows } });
    expect(withCounts.calibration.factor.metro).toBeCloseTo(0.5, 6);
    expect(withHubs(4).calibration).toEqual(UNCALIBRATED);
  });
});
