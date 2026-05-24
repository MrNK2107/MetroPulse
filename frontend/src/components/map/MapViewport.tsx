"use client";

import { useRef, useMemo, useCallback, useState } from "react";
import Map, { NavigationControl } from "react-map-gl/maplibre";
import DeckGL from "@deck.gl/react";
import { MapView } from "@deck.gl/core";
import { GeoJsonLayer } from "@deck.gl/layers";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import { MaskExtension } from "@deck.gl/extensions";
import { cellToLatLng } from "h3-js";
import { MAP_STYLE } from "@/lib/mapConfig";

// Hoist static instances to module scope to avoid per-render allocation
const MAP_VIEW = new MapView({ id: "map", controller: true });
const MASK_EXTENSION = new MaskExtension();
import { useSimulationStore } from "@/store/simulationStore";
import { formatDelta, metricToRGBA, heatmapWeight, heatmapColorRange, type MapMetricKey } from "@/lib/colorScale";
import { MapLegend } from "./MapLegend";
import { MapControlsHUD } from "./MapControlsHUD";
import type { HexCellState } from "@/types/simulation";
import "maplibre-gl/dist/maplibre-gl.css";

function getMetricVal(cell: HexCellState, metric: MapMetricKey): number {
  switch (metric) {
    case "delta":
      return cell.delta;
    case "jobDensity":
      return cell.jobDensity + cell.jobDensityInformal;
    case "congestion":
      return cell.congestion;
    case "realEstateIndex":
      return cell.realEstateIndex;
    case "floodRisk":
      return cell.floodRisk;
    default:
      return cell.delta;
  }
}

export function MapViewport() {
  const deckRef = useRef<any>(null);
  const frames = useSimulationStore((s) => s.frames);
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);
  const horizonMonths = useSimulationStore((s) => s.parsedScenario?.horizon_months ?? s.frames.length);
  const drawMode = useSimulationStore((s) => s.drawMode);
  const setPublicWorksZone = useSimulationStore((s) => s.setPublicWorksZone);
  const addZoneVertex = useSimulationStore((s) => s.addZoneVertex);
  const pendingVertices = useSimulationStore((s) => s.pendingVertices);
  const publicWorksZone = useSimulationStore((s) => s.publicWorksZone);
  const activeFrameIndex = useSimulationStore((s) => s.activeFrameIndex);
  const regionBoundary = useSimulationStore((s) => s.regionBoundary);

  // HUD States
  const activeVisualizationMode = useSimulationStore((s) => s.activeVisualizationMode);
  const activeMetric = useSimulationStore((s) => s.activeMetric);
  const mapViewState = useSimulationStore((s) => s.mapViewState);
  const setMapViewState = useSimulationStore((s) => s.setMapViewState);

  const [hoveredCell, setHoveredCell] = useState<{
    cell: HexCellState;
    x: number;
    y: number;
  } | null>(null);

  const currentFrame =
    frames.length > 0 && activeFrameIndex >= 0
      ? frames[Math.min(activeFrameIndex, frames.length - 1)]
      : null;

  // Pre-compute cellToLatLng positions once per frame (not per render cycle)
  const positionCache = useMemo(() => {
    if (!currentFrame) return new globalThis.Map<string, [number, number]>();
    const cache = new globalThis.Map<string, [number, number]>();
    for (const cell of currentFrame.cells) {
      const [lat, lng] = cellToLatLng(cell.h3Index);
      cache.set(cell.h3Index, [lng, lat]);
    }
    return cache;
  }, [currentFrame]);

  // Build mask data for the city boundary (visible in all modes, also used as mask source for heatmap)
  const maskData = useMemo<GeoJSON.FeatureCollection | null>(() => {
    if (!regionBoundary) return null;
    return {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: regionBoundary as GeoJSON.Geometry,
          properties: {},
        },
      ],
    };
  }, [regionBoundary]);

  const layers = useMemo(() => {
    const result: any[] = [];

    if (currentFrame) {
      if (activeVisualizationMode === "heatmap") {
        // Use a constant screen-space radius so heatmap blobs stay visually stable
        // regardless of zoom level. radiusMinPixels / radiusMaxPixels prevent extremes.
        result.push(
          new HeatmapLayer({
            id: `heatmap-layer-${activeMetric}`,
            data: currentFrame.cells,
            getPosition: (d: HexCellState) => positionCache.get(d.h3Index) ?? [0, 0],
            getWeight: (d: HexCellState) => {
              const val = getMetricVal(d, activeMetric);
              return heatmapWeight(val, activeMetric);
            },
            radiusPixels: 18,
            radiusMinPixels: 6,
            radiusMaxPixels: 60,
            intensity: 1.4,
            threshold: 0.05,
            colorRange: heatmapColorRange(activeMetric),
            // Clip heatmap to the exact city boundary polygon using MaskExtension
            extensions: maskData ? [MASK_EXTENSION] : [],
            maskId: maskData ? "city-boundary-mask" : undefined,
            maskByInstance: false,
            maskInverted: false,
            updateTriggers: {
              getWeight: [activeMetric],
              colorRange: [activeMetric],
            },
          })
        );
      } else {
        result.push(
          new H3HexagonLayer<HexCellState>({
            id: `hex-layer-${activeMetric}-${activeVisualizationMode}`,
            data: currentFrame.cells,
            getHexagon: (d) => d.h3Index,
            getFillColor: (d) => {
              const val = getMetricVal(d, activeMetric);
              return metricToRGBA(val, activeMetric);
            },
            getElevation: (d) => {
              const val = getMetricVal(d, activeMetric);
              if (activeMetric === "jobDensity") {
                return Math.max(10, val / 15);
              }
              if (activeMetric === "delta") {
                return Math.max(10, Math.abs(val) * 1500);
              }
              return Math.max(10, val * 350);
            },
            elevationScale: activeVisualizationMode === "3d" ? 12 : 0,
            extruded: activeVisualizationMode === "3d",
            coverage: 1.0, // Continuous filled grid overlay without gaps
            filled: true,
            stroked: false, // No borders separating cells
            opacity: 0.5, // 50% opacity as requested (40% - 60%)
            wireframe: false,
            pickable: true,
            autoHighlight: true,
            highlightColor: [255, 255, 255, 80],
            updateTriggers: {
              getFillColor: [activeMetric, activeVisualizationMode],
              getElevation: [activeMetric, activeVisualizationMode],
            },
          })
        );
      }
    }

    // Render the city boundary as a subtle outline for visual alignment reference.
    // In heatmap mode this layer also serves as the mask source for MaskExtension.
    if (maskData) {
      result.push(
        new GeoJsonLayer({
          id: "city-boundary-mask",
          data: maskData,
          stroked: true,
          filled: false,
          lineWidthMinPixels: 1.5,
          getLineColor: [148, 163, 184, 180], // slate-400 with some transparency
          getLineWidth: 1.5,
          pickable: false,
          // This layer is used as a mask source; operation is drawn as outline
          operation: "draw",
        })
      );
    }

    // Show drawn zone as GeoJson overlay
    if (publicWorksZone) {
      const zoneData: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: [{ type: "Feature", geometry: publicWorksZone as GeoJSON.Geometry, properties: {} }],
      };
      result.push(
        new GeoJsonLayer({
          id: "zone-overlay",
          data: zoneData,
          stroked: true,
          filled: true,
          lineWidthMinPixels: 3,
          getLineColor: [59, 130, 246, 220],
          getFillColor: [59, 130, 246, 60],
          getLineWidth: 3,
        })
      );
    }

    // Show pending polygon vertices during drawing
    if (drawMode === "polygon" && pendingVertices.length > 0) {
      const lineCoords: number[][] = pendingVertices.map(([lng, lat]) => [lng, lat]);
      const pendingData: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "LineString",
              coordinates: lineCoords,
            },
            properties: {},
          },
          {
            type: "Feature",
            geometry: {
              type: "MultiPoint",
              coordinates: lineCoords,
            },
            properties: {},
          },
        ],
      };
      result.push(
        new GeoJsonLayer({
          id: "pending-polygon",
          data: pendingData,
          stroked: true,
          filled: false,
          lineWidthMinPixels: 2,
          getLineColor: [96, 165, 250, 200],
          getLineWidth: 2,
          pointRadiusMinPixels: 6,
          getPointRadius: 6,
          getFillColor: [96, 165, 250, 200],
          pickable: false,
        })
      );
    }

    return result;
  }, [currentFrame, publicWorksZone, drawMode, pendingVertices, activeVisualizationMode, activeMetric, maskData, positionCache]);

  const handleClick = useCallback(
    (info: any) => {
      if (!info.coordinate) return;

      if (drawMode === "point") {
        setPublicWorksZone({
          type: "Point",
          coordinates: info.coordinate,
        });
      } else if (drawMode === "polygon") {
        addZoneVertex([info.coordinate[0], info.coordinate[1]]);
      }
    },
    [drawMode, setPublicWorksZone, addZoneVertex]
  );

  const handleHover = useCallback(
    (info: any) => {
      if (info.object && drawMode === "none") {
        setHoveredCell({ cell: info.object as HexCellState, x: info.x, y: info.y });
      } else {
        setHoveredCell(null);
      }
    },
    [drawMode]
  );

  const getCursor = useCallback(
    ({ isDragging }: { isDragging: boolean }) => {
      if (drawMode !== "none") return "crosshair";
      return isDragging ? "grabbing" : "grab";
    },
    [drawMode]
  );

  const handleViewStateChange = useCallback(
    (e: any) => {
      setMapViewState(e.viewState);
    },
    [setMapViewState]
  );

  return (
    <div className="relative w-full h-full">
      <DeckGL
        ref={deckRef}
        viewState={mapViewState}
        onViewStateChange={handleViewStateChange}
        controller={{ dragRotate: true, dragPan: true }}
        layers={layers}
        onClick={handleClick}
        onHover={handleHover}
        getCursor={getCursor}
        views={MAP_VIEW}
      >
        <Map
          mapStyle={MAP_STYLE}
          reuseMaps
          style={{ width: "100%", height: "100%" }}
        >
          <NavigationControl position="bottom-left" />
        </Map>
      </DeckGL>

      {/* Floating HUD Controls */}
      <MapControlsHUD />

      {/* Tooltip */}
      {hoveredCell && (
        <div
          className="absolute z-50 bg-dark-200/95 backdrop-blur-md border border-dark-100/50 rounded-xl px-4 py-3 text-xs pointer-events-none shadow-2xl transition-all"
          style={{ left: hoveredCell.x + 12, top: hoveredCell.y - 10 }}
        >
          <div className="text-gray-400 font-mono text-[9px] mb-2 flex items-center justify-between border-b border-dark-100 pb-1">
            <span>CELL ID</span>
            <span>{hoveredCell.cell.h3Index}</span>
          </div>
          <div className="space-y-1.5 font-sans min-w-[160px]">
            <div className="flex justify-between gap-4">
              <span className="text-gray-400">Delta</span>
              <span className={`font-mono font-semibold ${hoveredCell.cell.delta >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {formatDelta(hoveredCell.cell.delta)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-400">Activity (GDP)</span>
              <span className="text-gray-200 font-mono font-medium">{hoveredCell.cell.economicActivity.toFixed(1)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-400">Jobs (F / Inf)</span>
              <span className="text-gray-200 font-mono font-medium">
                {hoveredCell.cell.jobDensity.toFixed(0)} / {hoveredCell.cell.jobDensityInformal.toFixed(0)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-400">Real Estate Index</span>
              <span className="text-gray-200 font-mono font-medium">{hoveredCell.cell.realEstateIndex.toFixed(2)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-400">Congestion</span>
              <span className="text-gray-200 font-mono font-medium">{(hoveredCell.cell.congestion * 100).toFixed(0)}%</span>
            </div>
            {hoveredCell.cell.floodRisk > 0.1 && (
              <div className="flex justify-between gap-4">
                <span className="text-blue-400">Flood Risk</span>
                <span className="text-blue-300 font-mono font-medium">{(hoveredCell.cell.floodRisk * 100).toFixed(0)}%</span>
              </div>
            )}
            <div className="mt-2.5 max-w-[220px] border-t border-dark-100 pt-2 text-[10px] text-gray-500 italic leading-relaxed">
              {hoveredCell.cell.proof}
            </div>
          </div>
        </div>
      )}

      {currentFrame && <MapLegend />}

      {currentFrame && (
        <div className="absolute bottom-4 left-4 max-w-sm rounded-xl border border-dark-100/50 bg-dark-200/85 backdrop-blur-md px-3.5 py-2.5 text-white shadow-xl">
          <div className="text-xs font-mono font-bold text-gray-300 uppercase tracking-wider">
            Month {currentFrame.month} / {horizonMonths || currentFrame.month}
          </div>
          <div className="mt-1 text-xs font-medium text-gray-400">
            {pipelineStage === "simulating" ? "Animating:" : "Last loop:"}{" "}
            <span className="text-blue-400">{currentFrame.activeLoop}</span>
          </div>
        </div>
      )}
    </div>
  );
}
