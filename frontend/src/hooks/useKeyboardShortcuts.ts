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
      // Don't trigger shortcuts when typing in input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) {
        return;
      }

      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        const runBtn = document.querySelector("[data-run-btn]") as HTMLButtonElement | null;
        runBtn?.click();
        return;
      }

      // Ctrl+E — Export simulation results
      if ((e.ctrlKey || e.metaKey) && e.key === "e") {
        e.preventDefault();
        const exportBtn = document.querySelector("[data-export-btn]") as HTMLButtonElement | null;
        if (exportBtn) {
          exportBtn.click();
        } else {
          // Fallback: trigger export event for components that listen
          window.dispatchEvent(new CustomEvent("metropulse-export"));
        }
        return;
      }

      // Ctrl+Shift+S — Share simulation
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "S") {
        e.preventDefault();
        const shareBtn = document.querySelector("[data-share-btn]") as HTMLButtonElement | null;
        if (shareBtn) {
          shareBtn.click();
        } else {
          window.dispatchEvent(new CustomEvent("metropulse-share"));
        }
        return;
      }

      if (e.key === "Escape" && drawMode !== "none") {
        setDrawMode("none");
        e.preventDefault();
        return;
      }

      if (e.key === "?") {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("toggle-shortcuts-help"));
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
