"use client";

import { useSimulationStore } from "@/store/simulationStore";
import { SECTOR_LABELS } from "@/types/simulation";

export function FDISliders() {
  const parsedScenario = useSimulationStore((s) => s.parsedScenario);
  const adjustSectorDelta = useSimulationStore((s) => s.adjustSectorDelta);

  if (!parsedScenario) return null;

  const deltas = parsedScenario.sector_deltas;

  return (
    <section className="space-y-3 rounded-xl border border-dark-100/50 bg-dark-300/50 p-4 backdrop-blur-sm">
      <h3 className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
        Sector Adjustments (%)
      </h3>
      <div className="space-y-3">
        {Object.entries(SECTOR_LABELS).map(([key, label]) => {
          const value = deltas[key] ?? 0;
          const color =
            value > 0
              ? "text-emerald-400"
              : value < 0
                ? "text-red-400"
                : "text-gray-500";

          return (
            <div key={key} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-400">{label}</span>
                <span className={`text-[11px] font-mono font-bold ${color}`}>
                  {value > 0 ? "+" : ""}
                  {value}%
                </span>
              </div>
              <input
                type="range"
                min={-50}
                max={50}
                step={5}
                value={value}
                onChange={(e) => adjustSectorDelta(key, Number(e.target.value))}
                className="w-full cursor-pointer accent-blue-500"
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}
