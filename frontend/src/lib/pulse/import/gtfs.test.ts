import { strFromU8, strToU8, zipSync } from "fflate";
import { buildGtfsZip } from "./__fixtures__/gtfs";
import { parseGtfsZip } from "./gtfs";

const CHENNAI: [number, number] = [13.0827, 80.2707];

describe("parseGtfsZip", () => {
  it("reads 12 stations with modes from the route types that serve them", () => {
    const r = parseGtfsZip(buildGtfsZip(), CHENNAI);
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value).toHaveLength(12);
    expect(r.value.filter((s) => s.mode === "metro").map((s) => s.name)).toEqual(
      Array.from({ length: 6 }, (_, k) => `Metro Stop ${k}`)
    );
    expect(r.value.filter((s) => s.mode === "feeder")).toHaveLength(6);
    expect(r.report[0]).toMatch(/12 stations/);
  });

  it("drops a stop more than 60 km from the centre and reports it", () => {
    const far = 'FAR,"Far Away",14.5,81.9,0,';
    const r = parseGtfsZip(buildGtfsZip({ extraStops: [far] }), CHENNAI);
    expect(r.ok && r.value).toHaveLength(12);
    expect(r.ok && r.report.join(" ")).toMatch(/1 stop more than 60 km from the centre dropped/);
  });

  it("falls back to the name rule when stop_times.txt is missing", () => {
    const r = parseGtfsZip(buildGtfsZip({ withStopTimes: false }), CHENNAI);
    expect(r.ok && r.value.find((s) => s.name === "Metro Stop 1")?.mode).toBe("metro");
    expect(r.ok && r.value.find((s) => s.name === "Bus Halt 1")?.mode).toBe("feeder");
    expect(r.ok && r.report.join(" ")).toMatch(/stop_times/);
  });

  it("merges two stops with the same name within 150 m", () => {
    const dup = 'M0b,"Metro Stop 0",13.0832,80.2707,0,';
    const r = parseGtfsZip(buildGtfsZip({ extraStops: [dup] }), CHENNAI);
    expect(r.ok && r.value).toHaveLength(12);
  });

  it("keeps parent stations and skips their child platforms", () => {
    const parent = 'P1,"Central Station",13.0900,80.2800,1,';
    const child = 'P1a,"Central Station platform 1",13.0901,80.2801,0,P1';
    const r = parseGtfsZip(buildGtfsZip({ extraStops: [parent, child] }), CHENNAI);
    expect(r.ok && r.value.filter((s) => s.name.startsWith("Central"))).toEqual([
      { name: "Central Station", lat: 13.09, lng: 80.28, mode: "metro" },
    ]);
  });

  it("fails when stops.txt is missing or the file is not a zip", () => {
    const noStops = zipSync({ "routes.txt": strToU8("route_id,route_type\nR1,1\n") });
    expect(parseGtfsZip(noStops, CHENNAI)).toEqual({ ok: false, error: expect.stringMatching(/stops\.txt/) });
    expect(parseGtfsZip(new Uint8Array([1, 2, 3]), CHENNAI).ok).toBe(false);
  });
});

describe("parseGtfsZip on heavy feeds", () => {
  it("ignores shapes.txt and reads a stop_times with quoted fields", () => {
    const base = buildGtfsZip();
    const files = (require("fflate") as typeof import("fflate")).unzipSync(base);
    const st = strFromU8(files["stop_times.txt"]).replace(/\r\n/g, "\n").split("\n");
    // add a quoted headsign column with a comma, and a shapes.txt that is not valid CSV
    const rows = st.map((l, i) => (l ? (i === 0 ? l + ",stop_headsign" : l + ',"Central, via Mount Rd"') : l));
    files["stop_times.txt"] = strToU8(rows.join("\r\n"));
    files["shapes.txt"] = strToU8('"""unterminated,\n'.repeat(1000));
    const zip = zipSync(files, { level: 0 });
    const r = parseGtfsZip(zip, CHENNAI);
    expect(r.ok && r.value.filter((s) => s.mode === "metro")).toHaveLength(6);
  });
});

describe("GTFS extended route types", () => {
  it("treats 100-117 (rail) and 400-404 (urban rail) as metro", () => {
    const base = buildGtfsZip();
    const files = (require("fflate") as typeof import("fflate")).unzipSync(base);
    files["routes.txt"] = strToU8("route_id,route_short_name,route_type\r\nR1,Blue,401\r\nR2,500C,700\r\n");
    const r = parseGtfsZip(zipSync(files, { level: 0 }), CHENNAI);
    expect(r.ok && r.value.filter((s) => s.mode === "metro")).toHaveLength(6);
    expect(r.ok && r.value.filter((s) => s.mode === "feeder")).toHaveLength(6);
  });
});
