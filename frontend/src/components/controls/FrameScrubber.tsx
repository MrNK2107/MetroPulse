"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useSimulationStore } from "@/store/simulationStore";

export const FrameScrubber = React.memo(function FrameScrubber() {
  const frames = useSimulationStore((s) => s.frames);
  const activeFrameIndex = useSimulationStore((s) => s.activeFrameIndex);
  const setActiveFrameIndex = useSimulationStore((s) => s.setActiveFrameIndex);
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);

  const [isPlaying, setIsPlaying] = useState(false);

  const total = frames.length;
  const current = activeFrameIndex >= 0 ? activeFrameIndex : total - 1;

  const handleScrubberChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setActiveFrameIndex(Number(e.target.value));
      setIsPlaying(false); // Stop playing if user manual scrub
    },
    [setActiveFrameIndex]
  );

  // Auto-playback loop
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      const state = useSimulationStore.getState();
      if (state.activeFrameIndex >= state.frames.length - 1) {
        setIsPlaying(false); // Stop playing at the end
      } else {
        setActiveFrameIndex(state.activeFrameIndex + 1);
      }
    }, 450); // Advance frame every 450ms

    return () => clearInterval(interval);
  }, [isPlaying, total, setActiveFrameIndex]);

  if (pipelineStage !== "done" || total === 0) return null;

  const togglePlay = () => {
    if (current >= total - 1) {
      // If we are at the end, restart from first month
      setActiveFrameIndex(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  return (
    <div className="w-full flex items-center gap-4 bg-dark-300/40 border border-dark-100/30 rounded-xl px-4 py-2 mt-2">
      {/* Play/Pause Button */}
      <button
        onClick={togglePlay}
        className="flex items-center justify-center h-7 w-7 rounded-lg bg-blue-600/90 text-white hover:bg-blue-500 shadow-md shadow-blue-500/10 transition-all font-mono text-xs active:scale-90"
        title={isPlaying ? "Pause simulation" : "Play simulation playback"}
      >
        {isPlaying ? "❚❚" : "▶"}
      </button>

      {/* Month Indicator Label */}
      <span className="text-[11px] text-gray-400 font-mono w-[84px] select-none font-bold uppercase tracking-wider">
        Month {current + 1} / {total}
      </span>

      {/* Scrubber Range Slider */}
      <input
        type="range"
        min={0}
        max={total - 1}
        value={current}
        onChange={handleScrubberChange}
        className="flex-1 h-1 rounded-full appearance-none cursor-pointer bg-dark-300 accent-blue-500 outline-none"
      />
    </div>
  );
});
