"use client";

import { useSimulationStore } from "@/store/simulationStore";

const HORIZON_OPTIONS = [6, 12, 24, 60] as const;

export function TemporalSlider() {
  const parsedScenario = useSimulationStore((s) => s.parsedScenario);
  const setHorizonMonths = useSimulationStore((s) => s.setHorizonMonths);

  if (!parsedScenario) return null;

  const current = parsedScenario.horizon_months;

  return (
    <section className="space-y-2 rounded-xl border border-dark-100/50 bg-dark-300/50 p-4 backdrop-blur-sm">
      <h3 className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
        Simulation Horizon
      </h3>
      <div className="flex gap-1">
        {HORIZON_OPTIONS.map((months) => (
          <button
            key={months}
            onClick={() => setHorizonMonths(months)}
            className={`flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition-all ${
              current === months
                ? "bg-blue-600 text-white shadow-md shadow-blue-600/25"
                : "bg-dark-300 text-gray-400 hover:bg-dark-200 hover:text-gray-200"
            }`}
          >
            {months}mo
          </button>
        ))}
      </div>
      <p className="text-[10px] text-gray-600">
        {current === 6
          ? "Short-term shock analysis"
          : current === 12
            ? "Annual impact assessment"
            : current === 24
              ? "Standard 2-year forecast"
              : "Long-term structural change"}
      </p>
    </section>
  );
}
