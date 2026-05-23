"use client";

import { useCallback, useState } from "react";
import { useSimulationStore } from "@/store/simulationStore";

type DrawMode = "none" | "point" | "polygon";

export function DrawingToolbar() {
  const [mode, setMode] = useState<DrawMode>("none");
  const setPublicWorksZone = useSimulationStore((s) => s.setPublicWorksZone);
  const publicWorksZone = useSimulationStore((s) => s.params.publicWorksZone);

  const handleModeToggle = useCallback(
    (newMode: DrawMode) => {
      if (mode === newMode) {
        setMode("none");
      } else {
        setMode(newMode);
      }
    },
    [mode]
  );

  const handleClear = useCallback(() => {
    setPublicWorksZone(null);
    setMode("none");
  }, [setPublicWorksZone]);

  return (
    <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
      <div className="bg-dark-200/90 backdrop-blur-sm rounded-lg shadow-lg p-2 flex flex-col gap-1">
        <button
          onClick={() => handleModeToggle("point")}
          className={`px-3 py-1.5 text-xs rounded transition-colors ${
            mode === "point"
              ? "bg-blue-600 text-white"
              : "bg-dark-300 text-gray-300 hover:bg-dark-100"
          }`}
          title="Place a point zone"
        >
          Pin
        </button>
        <button
          onClick={() => handleModeToggle("polygon")}
          className={`px-3 py-1.5 text-xs rounded transition-colors ${
            mode === "polygon"
              ? "bg-blue-600 text-white"
              : "bg-dark-300 text-gray-300 hover:bg-dark-100"
          }`}
          title="Draw a polygon zone"
        >
          Polygon
        </button>
        {publicWorksZone && (
          <button
            onClick={handleClear}
            className="px-3 py-1.5 text-xs rounded bg-red-800/80 text-red-200 hover:bg-red-700 transition-colors"
            title="Clear drawn zone"
          >
            Clear
          </button>
        )}
      </div>
      {publicWorksZone && (
        <div className="bg-dark-200/90 backdrop-blur-sm rounded-lg shadow-lg px-3 py-1.5 text-xs text-green-400">
          Zone active
        </div>
      )}
    </div>
  );
}
