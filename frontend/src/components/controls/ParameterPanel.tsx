"use client";

import { useSimulationStore } from "@/store/simulationStore";
import { FDISliders } from "./FDISliders";
import { TemporalSlider } from "./TemporalSlider";
import { useWebSocket } from "@/hooks/useWebSocket";

export function ParameterPanel() {
  const params = useSimulationStore((s) => s.params);
  const status = useSimulationStore((s) => s.status);
  const { startSimulation } = useWebSocket();

  const isRunning = status === "running";
  const hasChanges =
    params.fdi.tech !== 0 ||
    params.fdi.manufacturing !== 0 ||
    params.fdi.realEstate !== 0 ||
    params.publicWorksZone !== null;

  const handleRun = () => {
    if (!hasChanges) return;
    const wsUrl =
      process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/simulate";
    startSimulation(params, wsUrl);
  };

  return (
    <div className="bg-dark-200 border-r border-dark-100 w-80 flex-shrink-0 flex flex-col h-full overflow-y-auto">
      <div className="p-4 border-b border-dark-100">
        <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
          Simulation Controls
        </h2>
      </div>

      <div className="flex-1 p-4 space-y-6">
        <div>
          <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
            Region
          </h3>
          <select className="w-full bg-dark-300 text-gray-200 rounded-lg px-3 py-2 text-sm border border-dark-100 focus:border-blue-500 focus:outline-none">
            <option value="nyc">New York City</option>
          </select>
        </div>

        <FDISliders />

        <div>
          <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
            Public Works Zone
          </h3>
          <p className="text-xs text-gray-500">
            Use the map toolbar to draw a zone
          </p>
        </div>

        <TemporalSlider />

        <button
          onClick={handleRun}
          disabled={!hasChanges || isRunning}
          className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all ${
            isRunning
              ? "bg-yellow-700 text-yellow-200 cursor-not-allowed animate-pulse"
              : hasChanges
                ? "bg-blue-600 text-white hover:bg-blue-500 active:scale-[0.98]"
                : "bg-dark-300 text-gray-500 cursor-not-allowed"
          }`}
        >
          {isRunning ? "Simulating..." : "Run Simulation"}
        </button>
      </div>
    </div>
  );
}
