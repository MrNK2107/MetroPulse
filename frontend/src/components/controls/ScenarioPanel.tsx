"use client";

import { useMemo } from "react";
import { useSimulationStore } from "@/store/simulationStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import { SECTOR_LABELS } from "@/types/simulation";
import { PresetSelector } from "./PresetSelector";
import { TemporalSlider } from "./TemporalSlider";
import { FDISliders } from "./FDISliders";

const EXAMPLES = [
  "What happens to Hyderabad if pharma FDI drops 40% but Smart City Mission continues for 24 months?",
  "Simulate a Bengaluru tech boom with Digital India and pressure on housing over two years.",
  "Mumbai manufacturing declines 30% while RERA compliance improves real estate stability.",
];

export function ScenarioPanel() {
  const scenarioText = useSimulationStore((s) => s.scenarioText);
  const parsed = useSimulationStore((s) => s.parsedScenario);
  const prediction = useSimulationStore((s) => s.prediction);
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);
  const error = useSimulationStore((s) => s.error);
  const setScenarioText = useSimulationStore((s) => s.setScenarioText);
  const resetAll = useSimulationStore((s) => s.resetAll);
  const { startSimulation, stopSimulation } = useWebSocket();

  const isRunning = !["idle", "done", "error"].includes(pipelineStage);
  const canRun = scenarioText.trim().length >= 4 && !isRunning;

  const deltas = useMemo(() => {
    if (!parsed) return [];
    return Object.entries(parsed.sector_deltas).filter(([, value]) => Math.abs(value) > 0);
  }, [parsed]);

  const handleRun = () => {
    if (!canRun) return;
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/simulate";
    startSimulation(scenarioText, wsUrl);
  };

  return (
    <aside className="w-[360px] bg-dark-200/95 border-r border-dark-100/50 h-full overflow-y-auto flex flex-col backdrop-blur-md shadow-2xl">
      {/* Brand Header */}
      <div className="p-5 border-b border-dark-100/40 bg-dark-300/40">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-md bg-blue-600 flex items-center justify-center font-bold text-xs shadow-md shadow-blue-500/20 text-white">
            M
          </div>
          <div>
            <h1 className="text-sm font-bold text-gray-100 uppercase tracking-widest font-sans">
              MetroPulse
            </h1>
            <p className="text-[10px] text-gray-500 uppercase font-medium tracking-wider">
              Urban Digital Twin Sandbox
            </p>
          </div>
        </div>
      </div>

      <div className="p-5 space-y-6 flex-1">
        {/* Quick Presets */}
        <PresetSelector />

        {/* Scenario Input */}
        <div>
          <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block mb-2">
            Simulation Prompt
          </label>
          <div className="relative group">
            <textarea
              value={scenarioText}
              onChange={(e) => setScenarioText(e.target.value)}
              rows={5}
              placeholder="Describe a city-level event or policy intervention..."
              className="w-full resize-none rounded-xl border border-dark-100/70 bg-dark-300/60 px-3.5 py-3 text-xs leading-relaxed text-gray-200 outline-none focus:border-blue-500/70 focus:bg-dark-300 transition-all font-sans"
            />
            <div className="absolute right-2.5 bottom-2.5 text-[9px] text-gray-600 font-mono">
              {scenarioText.length} chars
            </div>
          </div>
        </div>

        {/* Simulation Horizon */}
        <TemporalSlider />

        {/* FDI Sector Sliders */}
        <FDISliders />

        {/* Examples */}
        <div className="space-y-2">
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Predefined Scenarios</p>
          {EXAMPLES.map((example) => (
            <button
              key={example}
              onClick={() => setScenarioText(example)}
              className="block w-full rounded-xl border border-dark-100/40 bg-dark-300/35 px-3 py-2.5 text-left text-xs text-gray-400 hover:border-blue-500/40 hover:text-gray-200 hover:bg-dark-300/60 transition-all duration-200"
            >
              {example}
            </button>
          ))}
        </div>

        {error && (
          <div className="rounded-xl border border-red-800 bg-red-950/30 px-3.5 py-3 text-xs text-red-300 font-medium">
            <div className="font-bold uppercase text-[9px] text-red-400 mb-1">Error</div>
            {error}
          </div>
        )}

        {/* Run Controls */}
        <div className="flex gap-2 pt-2 border-t border-dark-100/30">
          {isRunning ? (
            <button
              onClick={stopSimulation}
              className="flex-1 rounded-xl bg-red-600 hover:bg-red-500 py-2.5 text-xs font-bold text-white shadow-lg shadow-red-500/10 transition-all duration-150 active:scale-95"
            >
              Stop Simulation
            </button>
          ) : (
            <button
              data-run-btn
              disabled={!canRun}
              onClick={handleRun}
              className={`flex-1 rounded-xl py-2.5 text-xs font-bold transition-all duration-150 active:scale-95 shadow-lg ${
                canRun
                  ? "bg-blue-600 text-white hover:bg-blue-500 shadow-blue-500/15"
                  : "bg-dark-300 text-gray-600 cursor-not-allowed border border-dark-100/50"
              }`}
            >
              Run Simulation
            </button>
          )}
          <button
            onClick={resetAll}
            className="rounded-xl border border-dark-100/80 bg-dark-300/50 px-4 py-2.5 text-xs font-semibold text-gray-400 hover:text-gray-200 hover:border-gray-600 transition-all active:scale-95"
          >
            Reset
          </button>
        </div>

        {/* Parsed Scenario HUD */}
        {parsed && (
          <section className="space-y-3 rounded-xl border border-dark-100/50 bg-dark-300/50 p-4 backdrop-blur-sm">
            <div className="border-b border-dark-100/30 pb-2">
              <span className="text-[9px] font-bold uppercase tracking-widest text-blue-400">Parsed Scenario Parameters</span>
              <p className="mt-1 text-sm font-bold text-gray-100 capitalize">
                {parsed.city.replace("_", " ")} &middot; {parsed.horizon_months} Months
              </p>
            </div>
            
            {deltas.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider block">Sector Modifications</span>
                <div className="flex flex-wrap gap-1.5">
                  {deltas.map(([sector, value]) => (
                    <span
                      key={sector}
                      className={`rounded-lg px-2 py-1 text-[10px] font-semibold flex items-center gap-1 ${
                        value >= 0 ? "bg-emerald-950/50 text-emerald-300 border border-emerald-500/20" : "bg-red-950/50 text-red-300 border border-red-500/20"
                      }`}
                    >
                      <span>{SECTOR_LABELS[sector] ?? sector}</span>
                      <span className="font-mono font-bold">{value > 0 ? "+" : ""}{value}%</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* FDI Sliders — adjust deltas before running */}
            <FDISliders />

            {parsed.policies_active.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider block">Active Policies</span>
                <div className="flex flex-wrap gap-1.5">
                  {parsed.policies_active.map((policy) => (
                    <span key={policy} className="rounded-lg bg-blue-950/50 border border-blue-500/20 px-2.5 py-1 text-[10px] font-semibold text-blue-300">
                      {policy}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-2 border-t border-dark-100/20 text-[10px] text-gray-500 italic leading-relaxed">
              {parsed.assumptions.join(" ")}
            </div>
          </section>
        )}

        {/* Before Simulation Expectations */}
        {prediction && (
          <section className="rounded-xl border border-dark-100/50 bg-dark-300/40 p-4">
            <span className="text-[9px] font-bold uppercase tracking-widest text-amber-500 block mb-2">Macro Predictions</span>
            <p className="text-xs leading-relaxed text-gray-400 font-sans">{prediction.reasoning}</p>
          </section>
        )}
      </div>
    </aside>
  );
}
