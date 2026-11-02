// MetroPulse service worker. Registered only in production builds (see ServiceWorker.tsx).
// The desk computes its city models in the browser, so once its pages and hashed
// assets are cached it keeps working offline. API, socket and cross-origin requests
// are never cached.
//
// The cache name carries the build id: ServiceWorker.tsx registers
// /sw.js?v=<NEXT_PUBLIC_BUILD_ID> (set in next.config.js at build time), so every
// deploy installs a new worker with a fresh cache and activate drops older ones.
const BUILD_ID = new URL(self.location.href).searchParams.get("v") || "dev";
const PREFIX = "metropulse-desk-";
const CACHE = PREFIX + BUILD_ID;
const OFFLINE_PAGE = "/offline.html";
const PAGES = ["/", "/desk", "/brief", "/favicon.svg", OFFLINE_PAGE];

const OFFLINE_HTML =
  '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
  "<title>MetroPulse is offline</title><p>You are offline and this page has not been saved on this device. " +
  "Reconnect and reload.</p>";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(PAGES))
      .catch(() => undefined)
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      // Only this app's caches from other builds (including the old fixed "metropulse-desk-v1").
      .then((names) => Promise.all(names.filter((n) => n.startsWith(PREFIX) && n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

function offlineResponse() {
  return caches.open(CACHE).then((cache) =>
    cache.match(OFFLINE_PAGE).then(
      (page) =>
        page ||
        new Response(OFFLINE_HTML, {
          status: 503,
          headers: { "Content-Type": "text/html; charset=utf-8" },
        })
    )
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws")) return;

  // Content-hashed build assets never change: cache first.
  if (url.pathname.startsWith("/_next/static/") || /\.(svg|png|woff2?)$/.test(url.pathname)) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((res) => {
            if (res.ok) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(request, copy));
            }
            return res;
          })
      )
    );
    return;
  }

  // Pages: network first, so a new deploy shows at once. Offline, only a cached copy of
  // this exact path and query is served (a shared /desk?city=...&incident=... link must
  // not silently open some other view); otherwise a small offline page.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(request, copy));
          }
          return res;
        })
        .catch(() =>
          caches
            .open(CACHE)
            .then((cache) => cache.match(url.pathname + url.search))
            .then((hit) => hit || offlineResponse())
        )
    );
  }
});
