"use client";

import { useSimulationStore } from "@/store/simulationStore";

const HORIZON_OPTIONS = [6, 12, 24, 60] as const;

export function TemporalSlider() {
  const horizonMonths = useSimulationStore((s) => s.params.horizonMonths);
  const setHorizonMonths = useSimulationStore((s) => s.setHorizonMonths);

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
        Projection Horizon
      </h3>
      <div className="flex gap-1">
        {HORIZON_OPTIONS.map((months) => (
          <button
            key={months}
            onClick={() => setHorizonMonths(months)}
            className={`flex-1 py-2 text-xs rounded-lg font-medium transition-all ${
              horizonMonths === months
                ? "bg-blue-600 text-white shadow-lg"
                : "bg-dark-300 text-gray-400 hover:bg-dark-100"
            }`}
          >
            {months}m
          </button>
        ))}
      </div>
    </div>
  );
}
