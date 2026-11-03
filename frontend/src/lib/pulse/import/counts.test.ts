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
