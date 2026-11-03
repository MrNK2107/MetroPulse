import { parseStationsCsv } from "./stations";

describe("parseStationsCsv", () => {
  it("reads name, latitude and longitude headers and defaults the mode to metro", () => {
    const r = parseStationsCsv("Name,Latitude,Longitude\nMajestic,12.9767,77.5713\nIndiranagar,12.9784,77.6408\n");
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value).toEqual([
      { name: "Majestic", lat: 12.9767, lng: 77.5713, mode: "metro" },
      { name: "Indiranagar", lat: 12.9784, lng: 77.6408, mode: "metro" },
    ]);
    expect(r.report[0]).toMatch(/2 stations/);
  });

  it("maps bus to feeder and accepts a type column", () => {
    const r = parseStationsCsv("name,lat,lon,type\nA,12.9,77.5,bus\nB,12.9,77.6,BRT\n");
    expect(r.ok && r.value.map((s) => s.mode)).toEqual(["feeder", "brt"]);
  });

  it("fails with the missing column named", () => {
    const r = parseStationsCsv("name,lng\nA,77.5\n");
    expect(r).toEqual({ ok: false, error: expect.stringMatching(/lat/) });
  });

  it("skips a row with a non-numeric latitude and reports it", () => {
    const r = parseStationsCsv("name,lat,lng\nA,abc,77.5\nB,12.9,77.6\n");
    expect(r.ok && r.value.map((s) => s.name)).toEqual(["B"]);
    expect(r.ok && r.report.join(" ")).toMatch(/1 row.*skipped/);
  });

  it("fails when there are no usable rows", () => {
    expect(parseStationsCsv("name,lat,lng\n").ok).toBe(false);
  });
});
