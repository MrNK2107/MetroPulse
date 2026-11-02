/**
 * public/sw.js runs in a service-worker global; here it is evaluated in a vm
 * context with small fakes for caches, fetch and the event API.
 */
import fs from "fs";
import path from "path";
import vm from "vm";

const SOURCE = fs.readFileSync(path.join(__dirname, "../../public/sw.js"), "utf8");
const ORIGIN = "https://metropulse.example";

type Stored = Map<string, { body: string }>;

function makeWorker(build: string | null, existing: Record<string, Record<string, string>> = {}) {
  const stores = new Map<string, Stored>();
  for (const [name, entries] of Object.entries(existing)) {
    stores.set(name, new Map(Object.entries(entries).map(([k, body]) => [k, { body }])));
  }
  const keyOf = (req: any) => {
    const u = new URL(typeof req === "string" ? req : req.url, ORIGIN);
    return u.pathname + u.search;
  };
  const open = async (name: string) => {
    if (!stores.has(name)) stores.set(name, new Map());
    const store = stores.get(name)!;
    return {
      put: async (req: any, res: any) => void store.set(keyOf(req), { body: res.body }),
      addAll: async (urls: string[]) => urls.forEach((u) => store.set(keyOf(u), { body: `precached ${u}` })),
      match: async (req: any) => store.get(keyOf(req)),
    };
  };
  const caches = {
    open,
    keys: async () => [...stores.keys()],
    delete: async (name: string) => stores.delete(name),
    match: async (req: any) => {
      for (const store of stores.values()) {
        const hit = store.get(keyOf(req));
        if (hit) return hit;
      }
      return undefined;
    },
  };
  const listeners: Record<string, (e: any) => void> = {};
  const self: any = {
    location: new URL(build === null ? "/sw.js" : `/sw.js?v=${build}`, ORIGIN),
    addEventListener: (type: string, fn: (e: any) => void) => (listeners[type] = fn),
    skipWaiting: () => undefined,
    clients: { claim: async () => undefined },
  };
  let network: (req: any) => Promise<any> = async () => {
    throw new TypeError("offline");
  };
  class FakeResponse {
    constructor(public body: string, public init: any = {}) {}
    get headers() {
      return { get: (k: string) => this.init.headers?.[k] ?? null };
    }
  }
  const context = vm.createContext({
    self,
    caches,
    URL,
    Promise,
    Response: FakeResponse,
    fetch: (req: any) => network(req),
  });
  vm.runInContext(SOURCE, context);

  const fire = async (type: string, extra: any = {}) => {
    let pending: Promise<any> | undefined;
    const event = {
      ...extra,
      waitUntil: (p: Promise<any>) => void (pending = p),
      respondWith: (p: Promise<any>) => void (pending = p),
    };
    listeners[type](event);
    return pending ? await pending : undefined;
  };
  const navigate = (url: string) => fire("fetch", { request: { url: ORIGIN + url, method: "GET", mode: "navigate" } });
  return {
    stores,
    fire,
    navigate,
    setNetwork: (fn: (req: any) => Promise<any>) => (network = fn),
  };
}

describe("service worker", () => {
  it("stamps the cache name with the build id from its script URL", async () => {
    const sw = makeWorker("abc123");
    await sw.fire("install");
    expect([...sw.stores.keys()]).toEqual(["metropulse-desk-abc123"]);
    expect(sw.stores.get("metropulse-desk-abc123")!.has("/offline.html")).toBe(true);
  });

  it("evicts caches from older builds on activate, leaving other apps' caches", async () => {
    const sw = makeWorker("new", {
      "metropulse-desk-old": { "/desk": "old" },
      "metropulse-desk-v1": { "/desk": "older" },
      "someone-else": { "/x": "x" },
    });
    await sw.fire("install");
    await sw.fire("activate");
    expect([...sw.stores.keys()].sort()).toEqual(["metropulse-desk-new", "someone-else"]);
  });

  it("offline, serves the cached copy of the same path and query", async () => {
    const sw = makeWorker("b1");
    await sw.fire("install");
    sw.setNetwork(async () => ({ ok: true, body: "brief for pune", clone() { return this; } }));
    await sw.navigate("/brief?city=pune");
    await new Promise((r) => setTimeout(r, 0)); // let the background cache write land
    sw.setNetwork(async () => {
      throw new TypeError("offline");
    });
    const res = await sw.navigate("/brief?city=pune");
    expect(res.body).toBe("brief for pune");
  });

  it("offline, never swaps a shared link for another page", async () => {
    const sw = makeWorker("b1");
    await sw.fire("install");
    // /desk is precached, but a link to /desk?city=delhi&incident=7 must not open the plain desk,
    // and /twin (not cached) must not fall back to /desk either.
    for (const url of ["/desk?city=delhi&incident=7", "/twin", "/brief?city=agra"]) {
      const res = await sw.navigate(url);
      expect(res.body).toBe("precached /offline.html");
    }
  });

  it("falls back to an inline offline page if even the offline page is missing", async () => {
    const sw = makeWorker("b2");
    const res = await sw.navigate("/desk?city=x");
    expect(String(res.body)).toContain("offline");
    expect(res.init.status).toBe(503);
  });

  it("uses a stable name when registered without a build id", async () => {
    const sw = makeWorker(null);
    await sw.fire("install");
    expect([...sw.stores.keys()]).toEqual(["metropulse-desk-dev"]);
  });
});
