import { findColumn, parseCsv } from "./csv";

describe("parseCsv", () => {
  it("strips a BOM, accepts CRLF and keeps a quoted comma inside a field", () => {
    const text = '﻿Name,Lat,Lng\r\n"Majestic, Kempegowda",12.9767,77.5713\r\n';
    const { header, rows } = parseCsv(text);
    expect(header).toEqual(["name", "lat", "lng"]);
    expect(rows).toEqual([["Majestic, Kempegowda", "12.9767", "77.5713"]]);
  });

  it("unescapes doubled quotes", () => {
    const { rows } = parseCsv('a,b\n"He said ""hi""",2\n');
    expect(rows[0][0]).toBe('He said "hi"');
  });

  it("skips blank lines and trims the header", () => {
    const { header, rows } = parseCsv(" A , B \n1,2\n\n3,4\n");
    expect(header).toEqual(["a", "b"]);
    expect(rows).toHaveLength(2);
  });

  it("keeps a newline inside a quoted field", () => {
    const { rows } = parseCsv('a,b\n"line1\nline2",2\n');
    expect(rows).toEqual([["line1\nline2", "2"]]);
  });
});

describe("findColumn", () => {
  it("returns the first header matching any synonym, else -1", () => {
    expect(findColumn(["stop_name", "latitude"], ["name", "stop_name"])).toBe(0);
    expect(findColumn(["stop_name", "latitude"], ["lng", "lon"])).toBe(-1);
  });
});
