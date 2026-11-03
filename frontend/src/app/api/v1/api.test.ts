/**
 * @jest-environment node
 */
import { GET as cities } from "./cities/route";
import { GET as city } from "./cities/[id]/route";
import { GET as incidents } from "./cities/[id]/incidents/route";
import { GET as siteScore } from "./cities/[id]/site-score/route";
import { GET as suggest } from "./cities/[id]/suggest/route";
import { POST as scenario } from "./cities/[id]/scenario/route";
import { GET as rest } from "./[...rest]/route";

const req = (url: string, init?: RequestInit) => new Request(`http://localhost${url}`, init);
const ctx = (id: string) => ({ params: { id } });

describe("API v1", () => {
  it("lists the 30 cities in the envelope with caching and CORS headers", async () => {
    const res = await cities(req("/api/v1/cities"));
    expect(res.status).toBe(200);
    expect(res.headers.get("cache-control")).toMatch(/max-age=3600/);
    expect(res.headers.get("access-control-allow-origin")).toBe("*");
    const body = await res.json();
    expect(body.success).toBe(true);
    expect(body.data).toHaveLength(30);
    expect(body.data[0]).toEqual(expect.objectContaining({ id: expect.any(String), name: expect.any(String), population: expect.any(Number) }));
    expect(body.meta).toEqual(expect.objectContaining({ model: "sample" }));
  });

  it("returns a city summary and a 404 envelope for an unknown city", async () => {
    const ok = await city(req("/api/v1/cities/pune"), ctx("pune"));
    expect(ok.status).toBe(200);
    expect((await ok.json()).data.headline).toMatch(/^Pune: /);
    const bad = await city(req("/api/v1/cities/atlantis"), ctx("atlantis"));
    expect(bad.status).toBe(404);
    expect(await bad.json()).toEqual({ success: false, data: null, error: { code: "city_not_found", message: expect.any(String) }, meta: expect.anything() });
  });

  it("lists this week's incidents", async () => {
    const res = await incidents(req("/api/v1/cities/chennai/incidents"), ctx("chennai"));
    const body = await res.json();
    expect(body.data.length).toBeGreaterThanOrEqual(3);
    const first = body.data[0];
    expect(typeof first.headline).toBe("string");
    expect(typeof first.likelyCause).toBe("string");
    expect(Array.isArray(first.ruleTrace)).toBe(true);
    expect(first.cells).toBeUndefined();
    expect(first.hexagons).toBeGreaterThanOrEqual(3);
  });

  it("scores a site and validates its query", async () => {
    const ok = await siteScore(req("/api/v1/cities/chennai/site-score?lat=13.0418&lng=80.2341&mode=metro"), ctx("chennai"));
    expect(ok.status).toBe(200);
    const body = await ok.json();
    expect(body.data.dailyBoardings).toBeGreaterThan(0);
    expect(body.data.walkCells).toBeUndefined();
    expect(body.data.formula).toMatch(/^score = 60/);
    const noLat = await siteScore(req("/api/v1/cities/chennai/site-score?lng=80.2341"), ctx("chennai"));
    expect(noLat.status).toBe(400);
    expect((await noLat.json()).error.code).toBe("bad_request");
    const badMode = await siteScore(req("/api/v1/cities/chennai/site-score?lat=13.04&lng=80.23&mode=tram"), ctx("chennai"));
    expect(badMode.status).toBe(400);
    const far = await siteScore(req("/api/v1/cities/chennai/site-score?lat=19.07&lng=72.87&mode=metro"), ctx("chennai"));
    expect(far.status).toBe(400);
  });

  it("suggests up to five sites", async () => {
    const res = await suggest(req("/api/v1/cities/chennai/suggest?mode=metro&k=9"), ctx("chennai"));
    const body = await res.json();
    expect(body.data).toHaveLength(5);
    expect(body.data[0]).toEqual(expect.objectContaining({ lat: expect.any(Number), lng: expect.any(Number), newBoardings: expect.any(Number) }));
    const one = await suggest(req("/api/v1/cities/chennai/suggest"), ctx("chennai"));
    expect((await one.json()).data).toHaveLength(3);
  });

  it("evaluates a posted scenario and rejects a malformed one", async () => {
    const good = await scenario(
      req("/api/v1/cities/chennai/scenario", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ mode: "metro", alignment: "elevated", stations: [{ lat: 13.0418, lng: 80.2341 }, { lat: 13.0418, lng: 80.2452 }] }),
      }),
      ctx("chennai")
    );
    expect(good.status).toBe(200);
    const body = await good.json();
    expect(body.data.boardings).toBeGreaterThan(0);
    expect(body.data.stations).toHaveLength(2);
    expect(body.data.stations[0].walkCells).toBeUndefined();
    const bad = await scenario(req("/api/v1/cities/chennai/scenario", { method: "POST", body: "{not json" }), ctx("chennai"));
    expect(bad.status).toBe(400);
    const empty = await scenario(req("/api/v1/cities/chennai/scenario", { method: "POST", body: JSON.stringify({ mode: "metro", stations: [] }) }), ctx("chennai"));
    expect(empty.status).toBe(400);
  });

  it("answers unknown routes with a 404 envelope", async () => {
    const res = await rest(req("/api/v1/nothing/here"));
    expect(res.status).toBe(404);
    expect((await res.json()).error.code).toBe("not_found");
  });
});

describe("API v1 input hardening", () => {
  it("rejects a prototype key as a mode with a 400 envelope", async () => {
    const res = await siteScore(req("/api/v1/cities/chennai/site-score?lat=13.04&lng=80.23&mode=constructor"), ctx("chennai"));
    expect(res.status).toBe(400);
    const s = await suggest(req("/api/v1/cities/chennai/suggest?mode=toString"), ctx("chennai"));
    expect(s.status).toBe(400);
  });

  it("rejects a null body and a partial cost table on the scenario endpoint", async () => {
    const nul = await scenario(req("/api/v1/cities/chennai/scenario", { method: "POST", body: "null" }), ctx("chennai"));
    expect(nul.status).toBe(400);
    const partial = await scenario(
      req("/api/v1/cities/chennai/scenario", {
        method: "POST",
        body: JSON.stringify({ mode: "metro", stations: [{ lat: 13.0418, lng: 80.2341 }], costs: { perKmCr: { elevated: 1 } } }),
      }),
      ctx("chennai")
    );
    expect(partial.status).toBe(400);
    const bad = await scenario(
      req("/api/v1/cities/chennai/scenario", { method: "POST", body: JSON.stringify({ mode: "metro", stations: [{ lat: 13.0418, lng: 80.2341 }], costs: "cheap" }) }),
      ctx("chennai")
    );
    expect(bad.status).toBe(400);
  });
});
