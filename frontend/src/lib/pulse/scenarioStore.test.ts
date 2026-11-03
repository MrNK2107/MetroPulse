import type { Scenario } from "./scenario";
import { exportScenarios, getScenario, importScenarios, listScenarios, removeScenario, saveScenario } from "./scenarioStore";

const make = (id: string, cityId = "chennai", updatedAt = "2026-11-03T00:00:00.000Z"): Scenario => ({
  id,
  cityId,
  name: `Line ${id}`,
  mode: "metro",
  alignment: "elevated",
  stations: [{ lat: 13.0418, lng: 80.2341 }],
  createdAt: "2026-11-01T00:00:00.000Z",
  updatedAt,
});

beforeEach(() => {
  window.localStorage.clear();
  importScenarios(JSON.stringify({ version: 1, scenarios: [] }), { replace: true });
});

describe("scenario library", () => {
  it("saves, lists newest first, gets and removes", () => {
    saveScenario(make("aaaaaaaa", "chennai", "2026-11-02T00:00:00.000Z"));
    saveScenario(make("bbbbbbbb", "chennai", "2026-11-03T00:00:00.000Z"));
    saveScenario(make("cccccccc", "pune"));
    expect(listScenarios("chennai").map((s) => s.id)).toEqual(["bbbbbbbb", "aaaaaaaa"]);
    expect(listScenarios()).toHaveLength(3);
    expect(getScenario("cccccccc")?.cityId).toBe("pune");
    removeScenario("aaaaaaaa");
    expect(getScenario("aaaaaaaa")).toBeNull();
    expect(window.localStorage.getItem("metropulse.scenarios.v1")).toContain("bbbbbbbb");
  });

  it("upserts by id and bumps updatedAt", () => {
    saveScenario(make("aaaaaaaa"));
    saveScenario({ ...make("aaaaaaaa"), name: "Renamed" });
    expect(listScenarios()).toHaveLength(1);
    expect(getScenario("aaaaaaaa")?.name).toBe("Renamed");
    expect(getScenario("aaaaaaaa")?.updatedAt > "2026-11-03T00:00:00.000Z").toBe(true);
  });

  it("exports and imports JSON, regenerating a colliding id", () => {
    saveScenario(make("aaaaaaaa"));
    const json = exportScenarios();
    expect(JSON.parse(json)).toEqual({ version: 1, scenarios: [expect.objectContaining({ id: "aaaaaaaa" })] });
    const r = importScenarios(json);
    expect(r).toEqual({ added: 1 });
    const ids = listScenarios().map((s) => s.id);
    expect(ids).toHaveLength(2);
    expect(ids).toContain("aaaaaaaa");
    expect(ids.filter((x) => x === "aaaaaaaa")).toHaveLength(1);
  });

  it("rejects another version, bad JSON and scenarios without stations", () => {
    expect(importScenarios(JSON.stringify({ version: 2, scenarios: [] })).error).toMatch(/version/i);
    expect(importScenarios("{nope").error).toBeDefined();
    expect(importScenarios(JSON.stringify({ version: 1, scenarios: [{ ...make("aaaaaaaa"), stations: [] }] }))).toEqual({ added: 0, error: expect.stringMatching(/station/i) });
  });

  it("keeps what was saved this session when localStorage throws", () => {
    const setItem = jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const getItem = jest.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    saveScenario(make("aaaaaaaa"));
    expect(listScenarios().map((s) => s.id)).toEqual(["aaaaaaaa"]);
    setItem.mockRestore();
    getItem.mockRestore();
  });
});
