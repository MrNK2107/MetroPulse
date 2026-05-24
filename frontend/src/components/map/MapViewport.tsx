"use client";

import { useRef, useMemo, useCallback } from "react";
import Map, { NavigationControl } from "react-map-gl/maplibre";
import DeckGL from "@deck.gl/react";
import { MapView } from "@deck.gl/core";
import { INITIAL_VIEW_STATE, MAP_STYLE } from "@/lib/mapConfig";
import { HexLayer } from "./HexLayer";
import { useSimulationStore } from "@/store/simulationStore";
import "maplibre-gl/dist/maplibre-gl.css";

export function MapViewport() {
  const deckRef = useRef<any>(null);
  const frames = useSimulationStore((s) => s.frames);
  const status = useSimulationStore((s) => s.status);

  const currentFrame = frames.length > 0 ? frames[frames.length - 1] : null;

  const layers = useMemo(() => {
    if (!currentFrame) return [];
    const hexLayer = new HexLayer({
      data: currentFrame.cells,
      resolution: 8,
      extruded: true,
    });
    return [hexLayer];
  }, [currentFrame]);

  const getCursor = useCallback(({ isDragging }: { isDragging: boolean }) => {
    return isDragging ? "grabbing" : "grab";
  }, []);

  return (
    <div className="relative w-full h-full">
      <DeckGL
        ref={deckRef}
        initialViewState={INITIAL_VIEW_STATE}
        controller={{ dragRotate: true, dragPan: true }}
        layers={layers}
        getCursor={getCursor}
        views={new MapView({ id: "map", controller: true })}
      >
        <Map
          mapStyle={MAP_STYLE}
          reuseMaps
          style={{ width: "100%", height: "100%" }}
        >
          <NavigationControl position="top-left" />
        </Map>
      </DeckGL>

      {status === "running" && currentFrame && (
        <div className="absolute bottom-4 left-4 bg-black/70 text-white px-3 py-1.5 rounded text-sm font-mono">
          Frame {currentFrame.month} / {currentFrame.month}
        </div>
      )}
    </div>
  );
}
