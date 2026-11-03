import { buildGtfsZip } from "./__fixtures__/gtfs";
import { handleGtfsRequest } from "./gtfsWorkerHandler";
import { parseGtfsOffThread } from "./gtfsWorkerClient.inline";

const CHENNAI: [number, number] = [13.0827, 80.2707];

describe("GTFS worker handler", () => {
  it("returns the parser result for a feed and a failure, never a throw, for garbage", () => {
    const ok = handleGtfsRequest({ bytes: buildGtfsZip(), centre: CHENNAI });
    expect(ok.ok && ok.value).toHaveLength(12);
    const bad = handleGtfsRequest({ bytes: new Uint8Array([0x50, 0x4b, 0x03, 0x04, 1, 2, 3]), centre: CHENNAI });
    expect(bad.ok).toBe(false);
    expect(handleGtfsRequest({ bytes: null as unknown as Uint8Array, centre: CHENNAI }).ok).toBe(false);
  });
});

describe("parseGtfsOffThread (inline fallback)", () => {
  it("resolves with the same result as the parser", async () => {
    const r = await parseGtfsOffThread(buildGtfsZip(), CHENNAI);
    expect(r.ok && r.value.filter((s) => s.mode === "metro")).toHaveLength(6);
  });
});
