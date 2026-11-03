import { normaliseStationName, parseCountsCsv } from "./counts";

describe("parseCountsCsv", () => {
  it("reads station and daily_boardings", () => {
    const r = parseCountsCsv("station,daily_boardings\nMajestic,42000\nIndiranagar,18000\n");
    expect(r.ok && r.value).toEqual([
      { station: "Majestic", dailyBoardings: 42000 },
      { station: "Indiranagar", dailyBoardings: 18000 },
    ]);
  });

  it("averages station,date,boardings over the dates", () => {
    const r = parseCountsCsv("station,date,boardings\nA,2026-10-01,100\nA,2026-10-02,300\nB,2026-10-01,50\n");
    expect(r.ok && r.value).toEqual([
      { station: "A", dailyBoardings: 200 },
      { station: "B", dailyBoardings: 50 },
    ]);
  });

  it("sums station,hour,boardings into one day", () => {
    const r = parseCountsCsv("station,hour,boardings\nA,8,100\nA,9,150\nA,18,250\n");
    expect(r.ok && r.value).toEqual([{ station: "A", dailyBoardings: 500 }]);
  });

  it("accepts synonym headers and skips non-numeric rows with a report", () => {
    const r = parseCountsCsv("stop_name,taps\nA,100\nB,n/a\n");
    expect(r.ok && r.value).toEqual([{ station: "A", dailyBoardings: 100 }]);
    expect(r.ok && r.report.join(" ")).toMatch(/1 row.*skipped/);
  });

  it("fails without a station or a value column", () => {
    expect(parseCountsCsv("foo,bar\n1,2\n").ok).toBe(false);
  });
});

describe("normaliseStationName", () => {
  it("drops metro/station words, punctuation and extra spaces", () => {
    expect(normaliseStationName("M.G. Road Metro Station")).toBe("mg road");
    expect(normaliseStationName("  Majestic  (Kempegowda) Stn ")).toBe("majestic kempegowda");
  });
});

describe("parseCountsDetailed", () => {
  it("returns a 24-hour share profile when counts are by hour, summed across stations", () => {
    const { parseCountsDetailed } = require("./counts") as typeof import("./counts");
    const r = parseCountsDetailed("station,hour,boardings\nA,8,100\nA,20,300\nB,20,100\nB,9,100\n");
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value.rows).toEqual([
      { station: "A", dailyBoardings: 400 },
      { station: "B", dailyBoardings: 200 },
    ]);
    const h = r.value.hourly!;
    expect(h).toHaveLength(24);
    expect(h.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 9);
    expect(h[20]).toBeCloseTo(400 / 600, 9);
    expect(h[8]).toBeCloseTo(100 / 600, 9);
    expect(r.report.join(" ")).toMatch(/hourly profile/i);
  });

  it("has no hourly profile for daily counts", () => {
    const { parseCountsDetailed } = require("./counts") as typeof import("./counts");
    const r = parseCountsDetailed("station,daily_boardings\nA,10\n");
    expect(r.ok && r.value.hourly).toBeUndefined();
  });
});
