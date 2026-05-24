"use client";

import { useEffect } from "react";
import { useSimulationStore } from "@/store/simulationStore";

export function useKeyboardShortcuts() {
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);
  const frames = useSimulationStore((s) => s.frames);
  const activeFrameIndex = useSimulationStore((s) => s.activeFrameIndex);
  const setActiveFrameIndex = useSimulationStore((s) => s.setActiveFrameIndex);
  const drawMode = useSimulationStore((s) => s.drawMode);
  const setDrawMode = useSimulationStore((s) => s.setDrawMode);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        const runBtn = document.querySelector("[data-run-btn]") as HTMLButtonElement;
        runBtn?.click();
        return;
      }

      if (e.key === "Escape" && drawMode !== "none") {
        setDrawMode("none");
        e.preventDefault();
        return;
      }

      if (pipelineStage === "done" && frames.length > 0) {
        const idx = activeFrameIndex >= 0 ? activeFrameIndex : frames.length - 1;
        if (e.key === "ArrowRight" && idx < frames.length - 1) {
          setActiveFrameIndex(idx + 1);
          e.preventDefault();
        } else if (e.key === "ArrowLeft" && idx > 0) {
          setActiveFrameIndex(idx - 1);
          e.preventDefault();
        }
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pipelineStage, frames.length, activeFrameIndex, drawMode, setDrawMode, setActiveFrameIndex]);
}
