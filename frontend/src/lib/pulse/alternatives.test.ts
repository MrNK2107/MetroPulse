import { getCity } from "./geo";
import { buildCityModel } from "./model";
import { evaluateScenario, Scenario } from "./scenario";
import { ALTERNATIVES_COLUMNS, alternativesCsv, alternativesMarkdown } from "./alternatives";

const model = buildCityModel(getCity("chennai")!);
const mk = (name: string, stations: Scenario["stations"]): Scenario => ({
  id: name.toLowerCase().padEnd(8, "x").slice(0, 8),
  cityId: "chennai",
  name,
  mode: "metro",
  alignment: "elevated",
  stations,
  createdAt: "2026-11-03T00:00:00.000Z",
  updatedAt: "2026-11-03T00:00:00.000Z",
});
const a = mk("Option A", [{ lat: 13.0418, lng: 80.2341 }, { lat: 13.0418, lng: 80.2452 }]);
const b = mk("Option B, long", [{ lat: 13.0827, lng: 80.2707 }]);
const rows = [
  { label: "A", s: a, r: evaluateScenario(model, a) },
  { label: "B", s: b, r: evaluateScenario(model, b) },
];

describe("alternatives table", () => {
  it("has the ten DPR columns and one line per option in CSV, quoting commas", () => {
    expect(ALTERNATIVES_COLUMNS).toHaveLength(10);
    const csv = alternativesCsv(rows);
    const lines = csv.trim().split("\n");
    expect(lines).toHaveLength(3);
    expect(lines[0].split(",")).toHaveLength(10);
    expect(lines[0]).toBe(
      "Option,Mode,Stations,Length (km),Daily boardings,New share,Walk-band coverage after,Capital cost (₹ cr),Cost per daily boarding (₹ lakh),Score"
    );
    expect(lines[1].startsWith("A: Option A,metro,2,")).toBe(true);
    expect(lines[2].startsWith('"B: Option B, long",metro,1,')).toBe(true);
  });

  it("renders a Markdown table with a separator row", () => {
    const md = alternativesMarkdown(rows).split("\n");
    expect(md[0]).toMatch(/^\| Option \| Mode \| Stations \|/);
    expect(md[1]).toMatch(/^\|( ?-+:? ?\|){10}$/);
    expect(md).toHaveLength(4);
    expect(md[2]).toContain("| A: Option A | metro | 2 |");
  });
});
