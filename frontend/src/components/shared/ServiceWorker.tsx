"use client";

import { useEffect } from "react";

/**
 * Registers /sw.js in production only. In development a service worker would cache
 * hot-reloaded chunks and serve stale code, so there it is skipped (and any earlier
 * registration on localhost is removed).
 */
export function ServiceWorker() {
  useEffect(() => {
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
    if (process.env.NODE_ENV !== "production") {
      navigator.serviceWorker
        .getRegistrations()
        .then((regs) => regs.forEach((r) => r.unregister()))
        .catch(() => undefined);
      return;
    }
    navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  }, []);
  return null;
}
