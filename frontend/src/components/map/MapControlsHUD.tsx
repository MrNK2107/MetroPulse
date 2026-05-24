"use client";

import React, { useCallback } from "react";
import { useSimulationStore, CITY_COORDS } from "@/store/simulationStore";
import { METRIC_SCALES, type MapMetricKey } from "@/lib/colorScale";

export const MapControlsHUD = React.memo(function MapControlsHUD() {
  const activeVisualizationMode = useSimulationStore((s) => s.activeVisualizationMode);
  const activeMetric = useSimulationStore((s) => s.activeMetric);
  const setActiveVisualizationMode = useSimulationStore((s) => s.setActiveVisualizationMode);
  const setActiveMetric = useSimulationStore((s) => s.setActiveMetric);
  const flyToCity = useSimulationStore((s) => s.flyToCity);
  const parsedScenario = useSimulationStore((s) => s.parsedScenario);

  const handleCityChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    if (e.target.value) {
      flyToCity(e.target.value);
    }
  }, [flyToCity]);

  const handleMetricChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setActiveMetric(e.target.value as MapMetricKey);
  }, [setActiveMetric]);

  const activeCityId = parsedScenario?.city.toLowerCase().replace(" ", "_") || "";

  return (
    <div className="absolute top-4 left-16 z-10 flex flex-wrap gap-2 max-w-xl md:max-w-none">
      {/* City Selector */}
      <div className="flex items-center gap-1.5 rounded-lg border border-dark-100/50 bg-dark-200/85 px-2.5 py-1.5 text-xs text-gray-200 backdrop-blur-md shadow-lg">
        <span className="text-gray-400 font-medium">City:</span>
        <select
          value={activeCityId}
          onChange={handleCityChange}
          className="bg-transparent text-gray-100 outline-none font-semibold cursor-pointer py-0.5"
        >
          <option value="" disabled className="bg-dark-300 text-gray-400">Select city...</option>
          {Object.entries(CITY_COORDS).map(([id, cfg]) => (
            <option key={id} value={id} className="bg-dark-300 text-gray-200">
              {cfg.name}
            </option>
          ))}
        </select>
      </div>

      {/* Visual Mode Selector */}
      <div className="flex items-center gap-1.5 rounded-lg border border-dark-100/50 bg-dark-200/85 p-1 text-xs text-gray-200 backdrop-blur-md shadow-lg">
        <button
          onClick={() => setActiveVisualizationMode("heatmap")}
          className={`px-2 py-1 rounded-md font-semibold transition-colors ${
            activeVisualizationMode === "heatmap"
              ? "bg-blue-600 text-white shadow-md shadow-blue-500/25"
              : "text-gray-400 hover:text-gray-200"
          }`}
          title="Trace continuous city density heatmap"
        >
          Heatmap
        </button>
        <button
          onClick={() => setActiveVisualizationMode("flat")}
          className={`px-2 py-1 rounded-md font-semibold transition-colors ${
            activeVisualizationMode === "flat"
              ? "bg-blue-600 text-white shadow-md shadow-blue-500/25"
              : "text-gray-400 hover:text-gray-200"
          }`}
          title="Render flat district cells (Choropleth)"
        >
          Flat Grid
        </button>
        <button
          onClick={() => setActiveVisualizationMode("3d")}
          className={`px-2 py-1 rounded-md font-semibold transition-colors ${
            activeVisualizationMode === "3d"
              ? "bg-blue-600 text-white shadow-md shadow-blue-500/25"
              : "text-gray-400 hover:text-gray-200"
          }`}
          title="Render 3D height columns"
        >
          3D Pillars
        </button>
      </div>

      {/* Metric Overlay Selector */}
      <div className="flex items-center gap-1.5 rounded-lg border border-dark-100/50 bg-dark-200/85 px-2.5 py-1.5 text-xs text-gray-200 backdrop-blur-md shadow-lg">
        <span className="text-gray-400 font-medium">Overlay:</span>
        <select
          value={activeMetric}
          onChange={handleMetricChange}
          className="bg-transparent text-gray-100 outline-none font-semibold cursor-pointer py-0.5"
        >
          {Object.entries(METRIC_SCALES).map(([key, scale]) => (
            <option key={key} value={key} className="bg-dark-300 text-gray-200">
              {scale.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
});
