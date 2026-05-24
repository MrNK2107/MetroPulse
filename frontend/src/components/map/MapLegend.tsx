"use client";

import React from "react";
import { useSimulationStore } from "@/store/simulationStore";
import { getLegendStops, METRIC_SCALES, type MapMetricKey } from "@/lib/colorScale";

function formatStopLabel(value: number, metric: MapMetricKey): string {
  if (metric === "delta") {
    return value > 0 ? `+${(value * 100).toFixed(0)}%` : `${(value * 100).toFixed(0)}%`;
  }
  if (metric === "congestion" || metric === "floodRisk") {
    return `${(value * 100).toFixed(0)}%`;
  }
  if (metric === "jobDensity") {
    return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : `${value}`;
  }
  return `${value.toFixed(1)}`;
}

export const MapLegend = React.memo(function MapLegend() {
  const activeMetric = useSimulationStore((s) => s.activeMetric);
  const stops = getLegendStops(activeMetric);
  const scale = METRIC_SCALES[activeMetric];

  return (
    <div className="absolute bottom-4 right-4 z-10 bg-dark-200/90 backdrop-blur-sm rounded-lg shadow-lg px-3 py-2 text-xs">
      <div className="text-gray-400 text-[10px] font-medium mb-1.5 uppercase tracking-wider">
        {scale.label}
      </div>
      <div className="flex items-center gap-2">
        {stops.map((stop) => (
          <div key={stop.value} className="flex flex-col items-center gap-0.5">
            <div
              className="w-4 h-4 rounded-sm"
              style={{ backgroundColor: stop.color }}
            />
            <span className="text-gray-500 text-[9px]">
              {formatStopLabel(stop.value, activeMetric)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
});
