"use client";

import { useSimulationStore } from "@/store/simulationStore";

export function LoadingOverlay() {
  const status = useSimulationStore((s) => s.status);
  const frames = useSimulationStore((s) => s.frames);
  const params = useSimulationStore((s) => s.params);

  if (status !== "running") return null;

  const current = frames.length;
  const total = params.horizonMonths;

  return (
    <div className="absolute inset-0 z-50 pointer-events-none">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="bg-dark-200/90 backdrop-blur-md rounded-2xl px-8 py-6 shadow-2xl border border-white/10 flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-200 text-sm font-medium">Simulating...</p>
          <p className="text-gray-500 text-xs font-mono">
            Frame {Math.min(current + 1, total)} / {total}
          </p>
        </div>
      </div>
    </div>
  );
}
