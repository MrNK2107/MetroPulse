import { useTwinStore } from "./twinStore";
import * as api from "@/lib/twinApi";
import type { Observation } from "@/types/twin";

jest.mock("@/lib/twinApi");
const mocked = api as jest.Mocked<typeof api>;

const o: Observation = {
  indicator: "population",
  name: "Population",
  unit: "people",
  period: "2011",
  value: 10,
  trustLabel: "fact",
  receipt: { sourceId: "s", sourceName: "S", datasetVersion: "v", license: "l", url: "u" },
};

beforeEach(() => useTwinStore.getState().clear());

describe("twinStore", () => {
  it("selectPlace loads observations", async () => {
    mocked.getObservations.mockResolvedValue([o]);
    const p = useTwinStore.getState().selectPlace("district:1");
    expect(useTwinStore.getState().loading).toBe(true);
    await p;
    const s = useTwinStore.getState();
    expect(s.selectedPlaceId).toBe("district:1");
    expect(s.observations).toEqual([o]);
    expect(s.loading).toBe(false);
    expect(s.error).toBeNull();
  });

  it("selectPlace records errors and clears loading", async () => {
    mocked.getObservations.mockRejectedValue(new Error("twin data not built"));
    await useTwinStore.getState().selectPlace("district:2");
    const s = useTwinStore.getState();
    expect(s.error).toBe("twin data not built");
    expect(s.loading).toBe(false);
    expect(s.observations).toEqual([]);
  });

  it("retry re-fetches the selected place and dismissError clears the message", async () => {
    mocked.getObservations.mockRejectedValueOnce(new Error("boom"));
    await useTwinStore.getState().selectPlace("district:3");
    expect(useTwinStore.getState().error).toBe("boom");

    mocked.getObservations.mockResolvedValueOnce([o]);
    await useTwinStore.getState().retry();
    expect(useTwinStore.getState().error).toBeNull();
    expect(useTwinStore.getState().observations).toEqual([o]);

    useTwinStore.setState({ error: "map failed" });
    useTwinStore.getState().dismissError();
    expect(useTwinStore.getState().error).toBeNull();
  });
});