"use client";

import { useSimulationStore } from "@/store/simulationStore";
import { useCallback, useState, useEffect } from "react";

const ERROR_HINTS: Record<string, string> = {
  parsing: "Could not understand the scenario. Try including a city name and a sector change.",
  predicting: "Scenario expectation generation failed. The simulation will still run with default assumptions.",
  simulating: "Simulation failed. The scenario may be too extreme — try a shorter horizon or smaller sector changes.",
  retrieving: "Could not retrieve case studies. This is non-critical — the simulation results are still valid.",
  synthesizing: "Evidence synthesis failed. The simulation results are available but the report may be incomplete.",
};

export function SimulationProgress() {
  const stage = useSimulationStore((s) => s.pipelineStage);
  const errorStage = useSimulationStore((s) => s.errorStage);
  const error = useSimulationStore((s) => s.error);
  const frames = useSimulationStore((s) => s.frames);
  const total = useSimulationStore((s) => s.parsedScenario?.horizon_months ?? 0);
  const [showToast, setShowToast] = useState(false);

  // Show success toast when simulation completes
  useEffect(() => {
    if (stage === "done") {
      setShowToast(true);
      const timer = setTimeout(() => setShowToast(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [stage]);

  const dismissError = useCallback(() => {
    useSimulationStore.setState({ error: null, errorStage: null, pipelineStage: "idle" });
  }, []);

  if (stage === "error" && error) {
    const hint = ERROR_HINTS[errorStage ?? ""] || error;
    return (
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-40 max-w-lg">
        <div className="rounded-xl border border-red-500/30 bg-dark-200/95 px-4 py-3 text-sm text-red-300 shadow-lg backdrop-blur-sm" role="alert" aria-live="assertive">
          <span className="font-semibold text-red-400">Error: </span>{hint}
          <button
            onClick={dismissError}
            className="ml-3 inline-flex items-center justify-center w-5 h-5 rounded-full text-red-400 hover:text-white hover:bg-red-500/50 transition-colors text-xs font-bold"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      </div>
    );
  }

  if (showToast) {
    return (
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-40 max-w-lg">
        <div className="rounded-xl border border-emerald-500/30 bg-dark-200/95 px-4 py-3 text-sm text-emerald-300 shadow-lg backdrop-blur-sm" role="alert" aria-live="polite">
          <span className="font-semibold text-emerald-400">✅</span> Simulation complete! Results are ready.
        </div>
      </div>
    );
  }

  if (["idle", "done"].includes(stage)) return null;

  const current = frames.length;
  const pct = stage === "simulating" && total > 0 ? Math.round((current / total) * 100) : 12;

  return (
    <div className="absolute top-0 left-0 right-0 z-40">
      <div className="h-1 bg-dark-100/50" role="progressbar" aria-live="polite" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Simulation progress">
        <div
          className="h-full bg-blue-500 transition-all duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="absolute top-3 left-1/2 -translate-x-1/2 rounded-full border border-white/10 bg-dark-200/90 px-3 py-1 text-xs font-mono text-gray-200 shadow-lg backdrop-blur-sm">
        {stage === "simulating" ? `Simulating ${current} / ${total}` : `${stage}...`}
      </div>
    </div>
  );
}
