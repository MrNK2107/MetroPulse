"use client";

import React from "react";
import { useSimulationStore } from "@/store/simulationStore";
import type { PipelineStage } from "@/types/simulation";

const STEPS: { stage: PipelineStage; label: string }[] = [
  { stage: "parsing", label: "Prompt" },
  { stage: "predicting", label: "Prediction" },
  { stage: "simulating", label: "Simulation" },
  { stage: "retrieving", label: "Evidence" },
  { stage: "synthesizing", label: "Recommendation" },
];

export const PipelineFlow = React.memo(function PipelineFlow() {
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);
  const stageHistory = useSimulationStore((s) => s.stageHistory);
  const latest = stageHistory[stageHistory.length - 1];

  // If the simulation hasn't run yet, hide the flow hud to keep screen empty and spacious
  if (pipelineStage === "idle") return null;

  return (
    <div className="flex flex-col items-center gap-1.5 rounded-xl border border-dark-100/50 bg-dark-200/80 backdrop-blur-md px-4 py-2 text-xs shadow-xl max-w-full">
      <div className="flex items-center gap-1 overflow-x-auto w-full no-scrollbar justify-center py-0.5">
        {STEPS.map((step, index) => {
          const history = stageHistory.find((entry) => entry.stage === step.stage);
          const active = pipelineStage === step.stage;
          const complete = Boolean(history && history.status === "complete");
          return (
            <div key={step.stage} className="flex items-center">
              <div
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[10px] font-semibold border transition-all duration-300 ${
                  active
                    ? "border-blue-500 bg-blue-950/60 text-blue-200 shadow-md shadow-blue-500/10 scale-105"
                    : complete
                      ? "border-emerald-800 bg-emerald-950/40 text-emerald-300"
                      : "border-dark-100/60 bg-dark-300/30 text-gray-500"
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full transition-all duration-300 ${
                    active ? "animate-pulse bg-blue-400" : complete ? "bg-emerald-400" : "bg-gray-700"
                  }`}
                />
                {step.label}
              </div>
              {index < STEPS.length - 1 && (
                <div className={`h-[1px] w-3.5 ${complete ? "bg-emerald-800/80" : "bg-dark-100/40"}`} />
              )}
            </div>
          );
        })}
      </div>
      {latest && (
        <p className="text-[10px] text-gray-400 font-sans font-medium animate-fade-in text-center px-2">
          {latest.message}
        </p>
      )}
    </div>
  );
});
