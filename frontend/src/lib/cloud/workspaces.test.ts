import type { Scenario } from "@/lib/pulse/scenario";
import { listScenarios, putScenario } from "@/lib/pulse/scenarioStore";
import { memoryStore, syncScenarios, toRow } from "./scenarioSync";
import { canEdit, memoryWorkspaces, Role } from "./workspaces";

const mk = (id: string, name: string, workspaceId?: string): Scenario => ({
  id,
  cityId: "chennai",
  name,
  mode: "metro",
  alignment: "elevated",
  stations: [{ lat: 13.0418, lng: 80.2341 }],
  createdAt: "2026-11-01T00:00:00.000Z",
  updatedAt: "2026-11-03T00:00:00.000Z",
  ...(workspaceId ? { workspaceId } : {}),
});

beforeEach(() => window.localStorage.clear());

describe("workspace store", () => {
  it("creates a workspace with the creator as owner, invites members with roles, lists mine", async () => {
    const ws = memoryWorkspaces({ id: "user-1", email: "owner@example.org" });
    const w = await ws.create("BMRCL Phase 3");
    expect(w).toEqual(expect.objectContaining({ name: "BMRCL Phase 3", ownerId: "user-1" }));
    await ws.invite(w.id, "planner@example.org", "editor");
    await ws.invite(w.id, "board@example.org", "viewer");
    const members = await ws.members(w.id);
    expect(members.map((m) => `${m.email}:${m.role}`).sort()).toEqual(["board@example.org:viewer", "owner@example.org:owner", "planner@example.org:editor"]);
    expect((await ws.list()).map((x) => x.id)).toEqual([w.id]);
    expect(await ws.roleOf(w.id)).toBe("owner");
  });

  it("knows which roles may edit", () => {
    expect(canEdit("owner")).toBe(true);
    expect(canEdit("editor")).toBe(true);
    expect(canEdit("viewer")).toBe(false);
    expect(canEdit(null as unknown as Role)).toBe(false);
  });
});

describe("syncScenarios scoped to a workspace", () => {
  it("pulls only that workspace's rows and pushes only lines tagged for it", async () => {
    const cloud = memoryStore([
      { ...toRow(mk("personal", "Mine"), "user-1"), workspace_id: null },
      { ...toRow(mk("team0001", "Team line"), "user-1"), workspace_id: "ws-1" },
      { ...toRow(mk("other001", "Other team"), "user-2"), workspace_id: "ws-2" },
    ]);
    putScenario(mk("local001", "Local team draft", "ws-1"));
    putScenario(mk("local002", "Local personal"));
    const r = await syncScenarios(cloud, "user-1", "chennai", "ws-1");
    expect(r).toEqual({ pulled: 1, pushed: 1 });
    expect(listScenarios("chennai").map((s) => s.name).sort()).toEqual(["Local personal", "Local team draft", "Team line"]);
    const rows = await cloud.list("chennai", "ws-1");
    expect(rows.map((x) => x.id).sort()).toEqual(["local001", "team0001"]);
    const personal = await syncScenarios(cloud, "user-1", "chennai", null);
    expect(personal).toEqual({ pulled: 1, pushed: 1 });
    expect(listScenarios("chennai").find((s) => s.id === "personal")?.workspaceId).toBeUndefined();
    expect(listScenarios("chennai").find((s) => s.id === "team0001")?.workspaceId).toBe("ws-1");
  });
});
