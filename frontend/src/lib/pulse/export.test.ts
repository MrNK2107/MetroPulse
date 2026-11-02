import { cellDay, csvField, incidentsToCsv, INCIDENT_CSV_HEADER } from "./export";
import { detectIncidents } from "./alerts";
import { getCity } from "./geo";
import { getCityModel } from "./model";

describe("csvField", () => {
  it("leaves plain values alone and quotes commas, quotes and newlines", () => {
    expect(csvField("T Nagar")).toBe("T Nagar");
    expect(csvField(42)).toBe("42");
    expect(csvField("a, b")).toBe('"a, b"');
    expect(csvField('say "hi"')).toBe('"say ""hi"""');
    expect(csvField("two\nlines")).toBe('"two\nlines"');
  });
});

describe("incidentsToCsv", () => {
  const model = getCityModel(getCity("chennai")!);
  const incidents = detectIncidents(model);

  it("writes a header and one row per incident, most severe first", () => {
    const lines = incidentsToCsv(incidents).trimEnd().split("\r\n");
    expect(lines[0]).toBe(INCIDENT_CSV_HEADER.join(","));
    expect(lines).toHaveLength(incidents.length + 1);
    expect(lines[1].startsWith(`1,${incidents[0].kind},`)).toBe(true);
  });

  it("writes only a header for a quiet week", () => {
    expect(incidentsToCsv([])).toBe(INCIDENT_CSV_HEADER.join(",") + "\r\n");
  });
});

describe("cellDay", () => {
  it("slices the 24 hours of the day that contains the hour", () => {
    const week = new Float32Array(2 * 168).map((_, i) => i);
    const base = new Float32Array(2 * 168);
    const d = cellDay(week, base, 1, 24 + 9);
    expect(d.now).toHaveLength(24);
    expect(d.now[0]).toBe(168 + 24);
    expect(d.at).toBe(9);
    expect(d.base.every((v) => v === 0)).toBe(true);
  });
});
