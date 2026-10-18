"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { PlaceCard } from "@/components/twin/PlaceCard";
import { PlaceSearch } from "@/components/twin/PlaceSearch";
import { getPlace } from "@/lib/twinApi";
import { useTwinStore } from "@/store/twinStore";
import type { PlaceDetail } from "@/types/twin";

const IndiaMap = dynamic(
  () => import("@/components/twin/IndiaMap").then((m) => ({ default: m.IndiaMap })),
  { ssr: false }
);

export default function Home() {
  const { selectedPlaceId, observations, loading, error, clear } = useTwinStore();
  const [place, setPlace] = useState<PlaceDetail | null>(null);

  useEffect(() => {
    if (!selectedPlaceId) {
      setPlace(null);
      return;
    }
    let live = true;
    getPlace(selectedPlaceId)
      .then((p) => live && setPlace(p))
      .catch(() => live && setPlace(null));
    return () => {
      live = false;
    };
  }, [selectedPlaceId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") clear();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [clear]);

  return (
    <main className="relative h-screen w-screen overflow-hidden" style={{ background: "var(--map-bg)" }}>
      <IndiaMap />
      <div className="absolute left-4 top-4 z-10">
        <PlaceSearch />
      </div>
      {error && (
        <div
          role="alert"
          className="absolute left-1/2 top-4 z-20 max-w-md -translate-x-1/2 rounded-md border border-red-700 bg-red-950/95 px-4 py-2 text-sm text-red-100"
        >
          {error}
        </div>
      )}
      {selectedPlaceId && (
        <aside
          aria-label="Place details"
          className="absolute bottom-0 right-0 top-0 z-10 w-96 max-w-full overflow-hidden border-l border-slate-700 bg-slate-950/95 p-4"
        >
          <button
            type="button"
            onClick={clear}
            aria-label="Close place details"
            className="absolute right-3 top-3 rounded px-2 py-1 text-sm text-slate-300 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          >
            Close
          </button>
          {loading && <p className="text-sm text-slate-400">Loading...</p>}
          {!loading && !error && (
            <PlaceCard
              name={place?.name ?? selectedPlaceId}
              stateName={place?.state?.name ?? null}
              observations={observations}
            />
          )}
        </aside>
      )}
    </main>
  );
}
