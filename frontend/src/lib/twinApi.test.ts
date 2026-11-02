import type * as TwinApi from "./twinApi";

type Reply = { ok?: boolean; status?: number; body?: unknown; badJson?: boolean; headers?: Record<string, string> };

function reply({ ok = true, status = 200, body, badJson, headers = {} }: Reply) {
  return {
    ok,
    status,
    headers: { get: (k: string) => headers[k.toLowerCase()] ?? null },
    json: badJson ? () => Promise.reject(new SyntaxError("bad json")) : () => Promise.resolve(body),
  };
}

const envelope = (data: unknown) => ({ success: true, data, error: null, meta: {} });

let fetchMock: jest.Mock;
let api: typeof TwinApi;

beforeEach(() => {
  fetchMock = jest.fn();
  (global as any).fetch = fetchMock;
  // Fresh module per test so the cached state-name promise never leaks between tests.
  jest.isolateModules(() => {
    api = require("./twinApi");
  });
});

afterEach(() => {
  delete process.env.NEXT_PUBLIC_API_URL;
});

describe("resolvePlace", () => {
  it("builds the query string and maps snake_case matches", async () => {
    fetchMock.mockResolvedValue(
      reply({
        body: envelope({
          matches: [
            { place_id: "district:572", name: "Pune", level: "district", state_code: "27", score: 100, method: "exact" },
            { place_id: "state:27", name: "Maharashtra", level: "state", score: 80, method: "fuzzy" },
          ],
          ambiguous: 1,
        }),
      })
    );
    const res = await api.resolvePlace("pune & co", { level: "district", state: "27" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/twin/places/resolve?q=pune+%26+co&level=district&state=27"
    );
    expect(res.ambiguous).toBe(true);
    expect(res.matches).toEqual([
      { placeId: "district:572", name: "Pune", level: "district", stateCode: "27", score: 100, method: "exact" },
      { placeId: "state:27", name: "Maharashtra", level: "state", stateCode: null, score: 80, method: "fuzzy" },
    ]);
  });

  it("uses NEXT_PUBLIC_API_URL and tolerates a missing matches list", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    fetchMock.mockResolvedValue(reply({ body: envelope({}) }));
    const res = await api.resolvePlace("x");
    expect(fetchMock.mock.calls[0][0]).toBe("https://api.example.test/api/twin/places/resolve?q=x");
    expect(res).toEqual({ matches: [], ambiguous: false });
  });
});

describe("errors", () => {
  it("surfaces the envelope error text (e.g. the 503 'not built' message)", async () => {
    fetchMock.mockResolvedValue(
      reply({ ok: false, status: 503, body: { success: false, data: null, error: "twin data not built — ..." } })
    );
    await expect(api.getPlace("district:1")).rejects.toThrow("twin data not built");
  });

  it("falls back to the status code for a non-JSON error body", async () => {
    fetchMock.mockResolvedValue(reply({ ok: false, status: 502, badJson: true }));
    await expect(api.getObservations("district:1")).rejects.toThrow("Request failed (502)");
  });

  it("treats success:false on a 200 as an error", async () => {
    fetchMock.mockResolvedValue(reply({ body: { success: false, error: "nope" } }));
    await expect(api.resolvePlace("x")).rejects.toThrow("nope");
  });

  it("propagates network failures", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(api.getPlace("district:1")).rejects.toThrow("Failed to fetch");
  });
});

describe("getPlace", () => {
  it("encodes the id and maps parent/state refs", async () => {
    fetchMock.mockResolvedValue(
      reply({
        body: envelope({
          place_id: "district:572",
          name: "Pune",
          level: "district",
          parent: { place_id: "state:27", name: "Maharashtra" },
          state: null,
        }),
      })
    );
    const p = await api.getPlace("district:572");
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/twin/places/district%3A572");
    expect(p).toEqual({
      placeId: "district:572",
      name: "Pune",
      level: "district",
      parent: { placeId: "state:27", name: "Maharashtra" },
      state: null,
    });
  });
});

describe("getObservations", () => {
  it("maps rows and turns missing values into null", async () => {
    fetchMock.mockResolvedValue(
      reply({
        body: envelope([
          {
            indicator: "population_total",
            name: "Total population",
            unit: "persons",
            period: "2011",
            value: 0,
            trust_label: "pattern",
            receipt: { source_id: "census", source_name: "Census", dataset_version: "v1", license: "OGL", url: "u" },
          },
          {
            indicator: "nightlights",
            name: "Nightlights",
            unit: "nW",
            receipt: { source_id: "viirs", source_name: "VIIRS" },
          },
        ]),
      })
    );
    const rows = await api.getObservations("district:572");
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://localhost:8000/api/twin/places/district%3A572/observations"
    );
    // 0 is a real value and must survive; absent fields become null, never 0.
    expect(rows[0].value).toBe(0);
    expect(rows[0].trustLabel).toBe("pattern");
    expect(rows[1]).toEqual({
      indicator: "nightlights",
      name: "Nightlights",
      unit: "nW",
      period: null,
      value: null,
      trustLabel: null,
      receipt: { sourceId: "viirs", sourceName: "VIIRS", datasetVersion: null, license: null, url: null },
    });
  });
});

describe("getStateNames", () => {
  const states = {
    type: "FeatureCollection",
    features: [
      { properties: { place_id: "state:27", name: "Maharashtra" } },
      { properties: { place_id: "state:29" } },
      { properties: {} },
    ],
  };

  it("indexes by place id and bare code, skipping incomplete features, and caches", async () => {
    fetchMock.mockResolvedValue(reply({ body: states }));
    const names = await api.getStateNames();
    expect(names).toEqual({ "state:27": "Maharashtra", "27": "Maharashtra" });
    await api.getStateNames();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/twin/boundaries/state");
  });

  it("does not cache a failure", async () => {
    fetchMock.mockResolvedValueOnce(reply({ ok: false, status: 503, body: {} }));
    await expect(api.getStateNames()).rejects.toThrow("Boundaries unavailable (503)");
    fetchMock.mockResolvedValueOnce(reply({ body: states }));
    await expect(api.getStateNames()).resolves.toHaveProperty("27", "Maharashtra");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

describe("getBoundaries", () => {
  const fc = { type: "FeatureCollection", features: [{ properties: { place_id: "state:27", name: "Maharashtra" } }] };

  afterEach(() => jest.useRealTimers());

  it("shares one request per level, including with getStateNames", async () => {
    fetchMock.mockResolvedValue(reply({ body: fc }));
    const [a, b] = await Promise.all([api.getBoundaries("state"), api.getBoundaries("state")]);
    expect(a).toBe(b);
    await api.getStateNames();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await api.getBoundaries("district");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenLastCalledWith("http://localhost:8000/api/twin/boundaries/district");
  });

  it("retries once on 429 after Retry-After seconds", async () => {
    jest.useFakeTimers();
    fetchMock
      .mockResolvedValueOnce(reply({ ok: false, status: 429, body: {}, headers: { "retry-after": "2" } }))
      .mockResolvedValueOnce(reply({ body: fc }));
    const p = api.getBoundaries("state");
    await jest.advanceTimersByTimeAsync(1900);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await jest.advanceTimersByTimeAsync(200);
    await expect(p).resolves.toEqual(fc);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("gives up after the second 429 and does not cache the failure", async () => {
    jest.useFakeTimers();
    const limited = reply({ ok: false, status: 429, body: { error: "Rate limit exceeded." }, headers: { "retry-after": "1" } });
    fetchMock.mockResolvedValueOnce(limited).mockResolvedValueOnce(limited);
    const p = api.getBoundaries("country");
    const settled = expect(p).rejects.toThrow("Rate limit exceeded.");
    await jest.advanceTimersByTimeAsync(1000);
    await settled;
    expect(fetchMock).toHaveBeenCalledTimes(2);
    fetchMock.mockResolvedValueOnce(reply({ body: fc }));
    await expect(api.getBoundaries("country")).resolves.toEqual(fc);
  });

  it("does not retry other errors", async () => {
    fetchMock.mockResolvedValueOnce(reply({ ok: false, status: 503, body: { error: "Twin not built" } }));
    await expect(api.getBoundaries("district")).rejects.toThrow("Twin not built");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
