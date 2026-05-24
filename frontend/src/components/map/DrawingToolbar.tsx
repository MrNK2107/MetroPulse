"use client";

import { useCallback } from "react";
import { useSimulationStore, type DrawMode } from "@/store/simulationStore";

export function DrawingToolbar() {
  const drawMode = useSimulationStore((s) => s.drawMode);
  const pendingVertices = useSimulationStore((s) => s.pendingVertices);
  const setDrawMode = useSimulationStore((s) => s.setDrawMode);
  const finishPolygon = useSimulationStore((s) => s.finishPolygon);
  const removeLastVertex = useSimulationStore((s) => s.removeLastVertex);
  const setPublicWorksZone = useSimulationStore((s) => s.setPublicWorksZone);
  const publicWorksZone = useSimulationStore((s) => s.publicWorksZone);

  const handleModeToggle = useCallback(
    (newMode: DrawMode) => {
      if (drawMode === newMode) {
        setDrawMode("none");
      } else {
        setDrawMode(newMode);
      }
    },
    [drawMode, setDrawMode]
  );

  const handleClear = useCallback(() => {
    setPublicWorksZone(null);
    setDrawMode("none");
  }, [setPublicWorksZone, setDrawMode]);

  return (
    <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
      <div className="bg-dark-200/90 backdrop-blur-sm rounded-lg shadow-lg p-2 flex flex-col gap-1">
        <button
          onClick={() => handleModeToggle("point")}
          className={`px-3 py-1.5 text-xs rounded transition-colors ${
            drawMode === "point"
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
            drawMode === "polygon"
              ? "bg-blue-600 text-white"
              : "bg-dark-300 text-gray-300 hover:bg-dark-100"
          }`}
          title="Draw a polygon zone"
        >
          Polygon
        </button>
        {drawMode === "polygon" && pendingVertices.length > 0 && (
          <>
            {pendingVertices.length >= 3 && (
              <button
                onClick={finishPolygon}
                className="px-3 py-1.5 text-xs rounded bg-green-700 text-green-200 hover:bg-green-600 transition-colors"
                title="Complete polygon"
              >
                Done ({pendingVertices.length} pts)
              </button>
            )}
            <button
              onClick={removeLastVertex}
              className="px-3 py-1.5 text-xs rounded bg-orange-800/80 text-orange-200 hover:bg-orange-700 transition-colors"
              title="Undo last point"
            >
              Undo
            </button>
          </>
        )}
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
      {drawMode !== "none" && (
        <div className="bg-blue-700/90 backdrop-blur-sm rounded-lg shadow-lg px-3 py-1.5 text-xs text-blue-200">
          Click map to place {drawMode === "point" ? "pin" : `vertex #${pendingVertices.length + 1}`}
        </div>
      )}
      {publicWorksZone && drawMode === "none" && (
        <div className="bg-dark-200/90 backdrop-blur-sm rounded-lg shadow-lg px-3 py-1.5 text-xs text-green-400">
          Zone active
        </div>
      )}
    </div>
  );
}
