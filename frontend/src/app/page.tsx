"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AgentChat } from "@/components/agent/AgentChat";
import { PlaceCard } from "@/components/twin/PlaceCard";
import { PlaceSearch } from "@/components/twin/PlaceSearch";
import { TwinNotBuilt, isNotBuiltError } from "@/components/twin/TwinNotBuilt";
import { getPlace } from "@/lib/twinApi";
import { useTwinStore } from "@/store/twinStore";
import type { PlaceDetail } from "@/types/twin";

const IndiaMap = dynamic(
  () => import("@/components/twin/IndiaMap").then((m) => ({ default: m.IndiaMap })),
  { ssr: false }
);

export default function Home() {
  const { selectedPlaceId, observations, loading, error, clear, retry, dismissError } =
    useTwinStore();
  const [place, setPlace] = useState<PlaceDetail | null>(null);

  useEffect(() => {
    setPlace(null);
    if (!selectedPlaceId) return;
    let live = true;
    getPlace(selectedPlaceId)
      .then((p) => live && p.placeId === selectedPlaceId && setPlace(p))
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
      {!selectedPlaceId && !error && (
        <p className="pointer-events-none absolute bottom-6 left-1/2 z-10 w-max max-w-[calc(100%-2rem)] -translate-x-1/2 rounded-lg border text-center border-slate-700 bg-slate-950/85 px-4 py-2 text-sm text-slate-300">
          Click a district or search above to see its indicators
        </p>
      )}
      {error && !selectedPlaceId && isNotBuiltError(error) && <TwinNotBuilt onDismiss={dismissError} />}
      {error && !selectedPlaceId && !isNotBuiltError(error) && (
        <div
          role="alert"
          className="absolute bottom-6 left-1/2 z-20 flex w-[calc(100%-2rem)] max-w-md -translate-x-1/2 items-start gap-3 rounded-md border border-red-700 bg-red-950/95 px-4 py-2 text-sm text-red-100"
        >
          <span className="flex-1">{error}</span>
          <button
            type="button"
            onClick={dismissError}
            aria-label="Dismiss error"
            className="rounded px-1 text-red-200 hover:bg-red-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-300"
          >
            Dismiss
          </button>
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
          {loading && (
            <div role="status" aria-busy="true" className="space-y-4 pt-1">
              <span className="sr-only">Loading place indicators</span>
              <div className="h-6 w-2/3 animate-pulse rounded bg-slate-800" />
              <div className="h-4 w-1/3 animate-pulse rounded bg-slate-800" />
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="h-12 animate-pulse rounded bg-slate-900" />
              ))}
            </div>
          )}
          {!loading && error && (
            <div role="alert" className="space-y-3 pt-8 text-sm">
              <p className="text-red-200">{error}</p>
              <button
                type="button"
                onClick={() => void retry()}
                className="rounded border border-slate-600 px-3 py-1 text-slate-100 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              >
                Try again
              </button>
            </div>
          )}
          {!loading && !error && (
            <PlaceCard
              name={place && place.placeId === selectedPlaceId ? place.name : "Loading place..."}
              stateName={place && place.placeId === selectedPlaceId ? place.state?.name ?? null : null}
              observations={observations}
            />
          )}
        </aside>
      )}
      <AgentChat />
    </main>
  );
}
