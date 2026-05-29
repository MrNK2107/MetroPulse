"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import { ConversationPanel } from "@/components/controls/ConversationPanel";
import { FrameScrubber } from "@/components/controls/FrameScrubber";
import { EvidencePanel } from "@/components/dashboard/EvidencePanel";
import { DataFreshnessPanel } from "@/components/dashboard/DataFreshnessPanel";
import { GroupImpactPanel } from "@/components/dashboard/GroupImpactPanel";
import { MetricPanel } from "@/components/dashboard/MetricPanel";
import { PipelineFlow } from "@/components/dashboard/PipelineFlow";
import { SimulationProgress } from "@/components/shared/LoadingOverlay";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useSimulationStore } from "@/store/simulationStore";

const MapViewport = dynamic(
  () => import("@/components/map/MapViewport").then((m) => ({ default: m.MapViewport })),
  { ssr: false }
);

const DrawingToolbar = dynamic(
  () => import("@/components/map/DrawingToolbar").then((m) => ({ default: m.DrawingToolbar })),
  { ssr: false }
);

export default function Home() {
  useKeyboardShortcuts();

  // Load city coordinates from API on mount (merges with static fallback)
  useEffect(() => {
    useSimulationStore.getState().loadCityCoords();
  }, []);

  const isLeftSidebarOpen = useSimulationStore((s) => s.isLeftSidebarOpen);
  const isRightSidebarOpen = useSimulationStore((s) => s.isRightSidebarOpen);
  const setLeftSidebarOpen = useSimulationStore((s) => s.setLeftSidebarOpen);
  const setRightSidebarOpen = useSimulationStore((s) => s.setRightSidebarOpen);

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-dark-400 text-gray-100 font-sans">
      {/* 1. Full Screen Map Viewport */}
      <div className="absolute inset-0 z-0 w-full h-full">
        <MapViewport />
      </div>

      {/* 2. Floating Header: Pipeline Stage Status */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 w-full max-w-2xl px-4 md:px-0 pointer-events-none">
        <div className="pointer-events-auto">
          <PipelineFlow />
        </div>
      </div>

      {/* Mobile Hamburger Button */}
      <button
        onClick={() => setLeftSidebarOpen(!isLeftSidebarOpen)}
        className="md:hidden absolute top-4 left-4 z-40 flex h-10 w-10 items-center justify-center rounded-xl border border-dark-100/50 bg-dark-200/90 text-gray-400 hover:text-white backdrop-blur-md shadow-lg transition-all"
        title="Toggle scenario panel"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Mobile Backdrop */}
      {(isLeftSidebarOpen || isRightSidebarOpen) && (
        <div
          className="md:hidden fixed inset-0 z-15 bg-black/50 backdrop-blur-sm"
          onClick={() => {
            setLeftSidebarOpen(false);
            setRightSidebarOpen(false);
          }}
        />
      )}

      {/* 3. Collapsible Left Panel Overlay: Scenario Simulator */}
      <div
        className={`absolute left-0 top-0 bottom-0 z-20 transition-all duration-300 transform ${
          isLeftSidebarOpen ? "translate-x-0" : "-translate-x-full"
        } w-full md:w-auto`}
      >
        <ConversationPanel />
      </div>

      {/* Toggle Left Sidebar Button (desktop) */}
      <button
        onClick={() => setLeftSidebarOpen(!isLeftSidebarOpen)}
        className={`hidden md:flex absolute top-1/2 -translate-y-1/2 z-30 h-14 w-5 items-center justify-center rounded-r-xl border border-l-0 border-dark-100/50 bg-dark-200/90 text-gray-400 hover:text-white backdrop-blur-md shadow-lg transition-all ${
          isLeftSidebarOpen ? "left-[360px]" : "left-0"
        }`}
        title={isLeftSidebarOpen ? "Hide scenario panel" : "Show scenario panel"}
      >
        <span className="text-[10px] font-bold font-mono">
          {isLeftSidebarOpen ? "◀" : "▶"}
        </span>
      </button>

      {/* 4. Collapsible Right Panel Overlay: Evidence & Proof */}
      <div
        className={`absolute right-0 top-0 bottom-0 z-20 transition-all duration-300 transform ${
          isRightSidebarOpen ? "translate-x-0" : "translate-x-full"
        } w-full md:w-auto`}
      >
        <EvidencePanel />
        <div className="px-4 pb-4">
          <GroupImpactPanel />
        </div>
      </div>

      {/* Toggle Right Sidebar Button (desktop) */}
      <button
        onClick={() => setRightSidebarOpen(!isRightSidebarOpen)}
        className={`hidden md:flex absolute top-1/2 -translate-y-1/2 z-30 h-14 w-5 items-center justify-center rounded-l-xl border border-r-0 border-dark-100/50 bg-dark-200/90 text-gray-400 hover:text-white backdrop-blur-md shadow-lg transition-all ${
          isRightSidebarOpen ? "right-[420px]" : "right-0"
        }`}
        title={isRightSidebarOpen ? "Hide evidence panel" : "Show evidence panel"}
      >
        <span className="text-[10px] font-bold font-mono">
          {isRightSidebarOpen ? "▶" : "◀"}
        </span>
      </button>

      {/* 5. Drawing Tool Overlay */}
      <div className="absolute right-4 top-20 z-10">
        <DrawingToolbar />
      </div>

      <div className="absolute left-1/2 top-20 z-10 w-[min(92vw,560px)] -translate-x-1/2 pointer-events-none">
        <div className="pointer-events-auto">
          <DataFreshnessPanel />
        </div>
      </div>

      {/* 6. Dynamic Bottom Drawer overlay: Playback controls and detailed metrics */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 w-full max-w-4xl px-4 md:px-0">
        <div className="flex flex-col gap-2 rounded-xl border border-dark-100/50 bg-dark-200/85 backdrop-blur-md p-3.5 shadow-2xl">
          {/* Metrics summary pills (clickable to expand charts) & Scrubber play block */}
          <MetricPanel />
          <FrameScrubber />
        </div>
      </div>

      {/* 7. Loading Overlays */}
      <SimulationProgress />
    </main>
  );
}
