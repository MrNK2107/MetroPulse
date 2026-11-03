import type { Scenario } from "@/lib/pulse/scenario";
import { getScenario, listScenarios, putScenario } from "@/lib/pulse/scenarioStore";
import { CloudStore, fromRow, memoryStore, ScenarioRow, syncScenarios, toRow } from "./scenarioSync";

const mk = (id: string, updatedAt: string, name = `Line ${id}`): Scenario => ({
  id,
  cityId: "chennai",
  name,
  mode: "metro",
  alignment: "elevated",
  stations: [{ lat: 13.0418, lng: 80.2341 }],
  createdAt: "2026-11-01T00:00:00.000Z",
  updatedAt,
});

beforeEach(() => window.localStorage.clear());

describe("scenario rows", () => {
  it("round-trips a scenario through a table row with the owner id", () => {
    const s = mk("aaaaaaaa", "2026-11-03T00:00:00.000Z");
    const row = toRow(s, "user-1");
    expect(row).toEqual(expect.objectContaining({ id: "aaaaaaaa", user_id: "user-1", city_id: "chennai", mode: "metro", updated_at: s.updatedAt }));
    expect(fromRow(row)).toEqual(s);
  });
});

describe("syncScenarios", () => {
  it("pulls cloud lines into the local library, pushes local-only ones, newest wins", async () => {
    const cloud: CloudStore = memoryStore([
      toRow(mk("cloud001", "2026-11-03T10:00:00.000Z", "Cloud only"), "user-1"),
      toRow(mk("shared01", "2026-11-03T12:00:00.000Z", "Cloud newer"), "user-1"),
    ]);
    putScenario(mk("local001", "2026-11-02T00:00:00.000Z", "Local only"));
    putScenario(mk("shared01", "2026-11-03T11:00:00.000Z", "Local older"));
    const r = await syncScenarios(cloud, "user-1", "chennai");
    expect(r).toEqual({ pulled: 2, pushed: 1 });
    const names = listScenarios("chennai").map((s) => s.name).sort();
    expect(names).toEqual(["Cloud newer", "Cloud only", "Local only"]);
    expect(getScenario("shared01")?.name).toBe("Cloud newer");
    const rows = await cloud.list("chennai");
    expect(rows.map((x: ScenarioRow) => x.id).sort()).toEqual(["cloud001", "local001", "shared01"]);
  });

  it("pushes a local line that is newer than the cloud copy", async () => {
    const cloud = memoryStore([toRow(mk("shared01", "2026-11-03T10:00:00.000Z", "Cloud older"), "user-1")]);
    putScenario(mk("shared01", "2026-11-03T12:00:00.000Z", "Local newer"));
    const r = await syncScenarios(cloud, "user-1", "chennai");
    expect(r).toEqual({ pulled: 0, pushed: 1 });
    expect((await cloud.list("chennai"))[0].name).toBe("Local newer");
  });
});
