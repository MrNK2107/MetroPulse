"use client";

import { useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { WebMercatorViewport, type PickingInfo } from "@deck.gl/core";
import { GeoJsonLayer } from "@deck.gl/layers";
import { boundariesUrl } from "@/lib/twinApi";
import { useTwinStore } from "@/store/twinStore";
import type { BoundaryLevel } from "@/types/twin";

type FC = { features: any[] };

const INITIAL_VIEW = { longitude: 82.8, latitude: 22.5, zoom: 3.8 };

function useBoundary(level: BoundaryLevel): { data: FC | null; failed: boolean } {
  const [data, setData] = useState<FC | null>(null);
  const [failed, setFailed] = useState(false);
  const setError = (m: string) => useTwinStore.setState({ error: m });
  useEffect(() => {
    let live = true;
    fetch(boundariesUrl(level))
      .then(async (r) => {
        if (!r.ok) {
          const body = await r.json().catch(() => null);
          throw new Error(body?.error || `Boundaries unavailable (${r.status})`);
        }
        return r.json();
      })
      .then((d) => live && setData(d))
      .catch((e) => {
        if (!live) return;
        setFailed(true);
        setError(e instanceof Error ? e.message : "Map data failed to load");
      });
    return () => {
      live = false;
    };
  }, [level]);
  return { data, failed };
}

function bounds(geom: any): [[number, number], [number, number]] | null {
  let minX = Infinity,
    minY = Infinity,
    maxX = -Infinity,
    maxY = -Infinity;
  const walk = (c: any) => {
    if (typeof c[0] === "number") {
      minX = Math.min(minX, c[0]);
      maxX = Math.max(maxX, c[0]);
      minY = Math.min(minY, c[1]);
      maxY = Math.max(maxY, c[1]);
    } else c.forEach(walk);
  };
  if (!geom?.coordinates) return null;
  walk(geom.coordinates);
  return Number.isFinite(minX)
    ? [
        [minX, minY],
        [maxX, maxY],
      ]
    : null;
}

export function IndiaMap() {
  const selectedPlaceId = useTwinStore((s) => s.selectedPlaceId);
  const selectPlace = useTwinStore((s) => s.selectPlace);
  const { data: district, failed: districtFailed } = useBoundary("district");
  const { data: state } = useBoundary("state");
  const { data: country } = useBoundary("country");
  const [viewState, setViewState] = useState<any>(INITIAL_VIEW);
  const [hovered, setHovered] = useState<string | null>(null);

  // Fly to the selected district's bounds.
  useEffect(() => {
    if (!selectedPlaceId || !district) return;
    const f = district.features.find((x) => x.properties?.place_id === selectedPlaceId);
    const b = f && bounds(f.geometry);
    if (!b) return;
    const { longitude, latitude, zoom } = new WebMercatorViewport({
      width: window.innerWidth || 1000,
      height: window.innerHeight || 700,
    }).fitBounds(b, { padding: 120 });
    setViewState({
      longitude,
      latitude,
      zoom: Math.min(zoom, 9),
      transitionDuration: 800,
    });
  }, [selectedPlaceId, district]);

  const layers = useMemo(
    () => [
      new GeoJsonLayer({
        id: "country",
        data: (country ?? { type: "FeatureCollection", features: [] }) as any,
        stroked: true,
        filled: false,
        getLineColor: [143, 179, 217, 255],
        getLineWidth: 2,
        lineWidthUnits: "pixels",
      }),
      new GeoJsonLayer({
        id: "district",
        data: (district ?? { type: "FeatureCollection", features: [] }) as any,
        pickable: true,
        stroked: true,
        filled: true,
        getFillColor: (f: any) => {
          const id = f.properties?.place_id;
          if (id === selectedPlaceId) return [255, 159, 28, 85];
          if (id === hovered) return [255, 255, 255, 40];
          return [0, 0, 0, 0];
        },
        getLineColor: [44, 74, 110, 255],
        getLineWidth: 1,
        lineWidthUnits: "pixels",
        updateTriggers: { getFillColor: [selectedPlaceId, hovered] },
      }),
      new GeoJsonLayer({
        id: "state",
        data: (state ?? { type: "FeatureCollection", features: [] }) as any,
        pickable: false,
        stroked: true,
        filled: false,
        getLineColor: [90, 130, 180, 255],
        getLineWidth: 2,
        lineWidthUnits: "pixels",
      }),
    ],
    [country, district, state, selectedPlaceId, hovered]
  );

  return (
    <div className="absolute inset-0" style={{ background: "var(--map-bg)" }}>
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: v }) => setViewState(v)}
        controller
        layers={layers}
        onHover={(i: PickingInfo) => setHovered(i.object?.properties?.place_id ?? null)}
        onClick={(i: PickingInfo) => {
          const id = i.object?.properties?.place_id;
          if (id) void selectPlace(id);
        }}
        getCursor={({ isHovering }) => (isHovering ? "pointer" : "grab")}
      />
      {!district && !districtFailed && (
        <div
          role="status"
          className="pointer-events-none absolute inset-0 flex items-center justify-center"
        >
          <span className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950/85 px-4 py-2 text-sm text-slate-300">
            <span className="h-2 w-2 animate-pulse rounded-full bg-sky-400" aria-hidden="true" />
            Loading district boundaries...
          </span>
        </div>
      )}
    </div>
  );
}
