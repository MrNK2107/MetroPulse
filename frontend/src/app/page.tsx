"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { FrameScrubber } from "@/components/controls/FrameScrubber";
import { DataFreshnessPanel } from "@/components/dashboard/DataFreshnessPanel";
import { GroupImpactPanel } from "@/components/dashboard/GroupImpactPanel";
import { MetricPanel } from "@/components/dashboard/MetricPanel";
import { PipelineFlow } from "@/components/dashboard/PipelineFlow";
import { SimulationProgress } from "@/components/shared/SimulationProgress";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { ConversationPanelSkeleton, EvidencePanelSkeleton } from "@/components/shared/Skeleton";
import { KeyboardShortcutsHelp } from "@/components/shared/KeyboardShortcutsHelp";
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

const ConversationPanel = dynamic(
  () => import("@/components/controls/ConversationPanel").then((m) => ({ default: m.ConversationPanel })),
  {
    ssr: false,
    loading: () => <ConversationPanelSkeleton />,
  }
);

const EvidencePanel = dynamic(
  () => import("@/components/dashboard/EvidencePanel").then((m) => ({ default: m.EvidencePanel })),
  {
    ssr: false,
    loading: () => <EvidencePanelSkeleton />,
  }
);

export default function Home() {
  useKeyboardShortcuts();

  // Keyboard shortcuts help modal
  const [showShortcuts, setShowShortcuts] = useState(false);

  useEffect(() => {
    const handler = () => setShowShortcuts((prev) => !prev);
    window.addEventListener("toggle-shortcuts-help", handler);
    return () => window.removeEventListener("toggle-shortcuts-help", handler);
  }, []);

  // Dark mode toggle — stored in localStorage
  const [isDark, setIsDark] = useState(true);
  useEffect(() => {
    const stored = localStorage.getItem("metropulse-theme");
    if (stored === "light") setIsDark(false);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("light", !isDark);
    localStorage.setItem("metropulse-theme", isDark ? "dark" : "light");
  }, [isDark]);

  // Load city coordinates from API on mount (merges with static fallback)
  useEffect(() => {
    useSimulationStore.getState().loadCityCoords();
  }, []);

  const isLeftSidebarOpen = useSimulationStore((s) => s.isLeftSidebarOpen);
  const isRightSidebarOpen = useSimulationStore((s) => s.isRightSidebarOpen);
  const setLeftSidebarOpen = useSimulationStore((s) => s.setLeftSidebarOpen);
  const setRightSidebarOpen = useSimulationStore((s) => s.setRightSidebarOpen);

  const toggleDark = useCallback(() => setIsDark((d) => !d), []);

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-dark-400 text-gray-100 font-sans">
      {/* 1. Full Screen Map Viewport */}
      <div className="absolute inset-0 z-0 w-full h-full">
        <ErrorBoundary name="Map">
          <MapViewport />
        </ErrorBoundary>
      </div>

      {/* 2. Floating Header: Pipeline Stage Status */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 w-full max-w-2xl px-4 md:px-0 pointer-events-none">
        <div className="pointer-events-auto">
          <ErrorBoundary name="Pipeline">
            <PipelineFlow />
          </ErrorBoundary>
        </div>
      </div>

      {/* Top-right controls: Dark mode toggle + Shortcuts help */}
      <div className="absolute top-4 right-4 z-30 flex items-center gap-1.5">
        <button
          onClick={toggleDark}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-dark-100/50 bg-dark-200/90 text-gray-400 hover:text-white backdrop-blur-md shadow-lg transition-all text-xs"
          title={isDark ? "Switch to light mode" : "Switch to dark mode"}
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDark ? "☀️" : "🌙"}
        </button>
        <button
          onClick={() => setShowShortcuts(true)}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-dark-100/50 bg-dark-200/90 text-gray-400 hover:text-white backdrop-blur-md shadow-lg transition-all"
          title="Keyboard shortcuts (?)"
          aria-label="Show keyboard shortcuts"
        >
          <span className="text-[11px] font-bold font-mono">?</span>
        </button>
      </div>

      {/* Mobile Hamburger Button */}
      <button
        onClick={() => { setLeftSidebarOpen(!isLeftSidebarOpen); if (!isLeftSidebarOpen) setRightSidebarOpen(false); }}
        className="md:hidden absolute top-4 left-4 z-40 flex h-10 w-10 items-center justify-center rounded-xl border border-dark-100/50 bg-dark-200/90 text-gray-400 hover:text-white backdrop-blur-md shadow-lg transition-all"
        aria-label="Toggle scenario panel"
        aria-expanded={isLeftSidebarOpen}
        title="Toggle scenario panel"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Mobile Backdrop */}
      {(isLeftSidebarOpen || isRightSidebarOpen) && (
        <div
          className="md:hidden fixed inset-0 z-[15] bg-black/50 backdrop-blur-sm"
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
        <ErrorBoundary name="Conversation">
          <ConversationPanel />
        </ErrorBoundary>
      </div>

      {/* Toggle Left Sidebar Button (desktop) */}
      <button
        onClick={() => { setLeftSidebarOpen(!isLeftSidebarOpen); if (!isLeftSidebarOpen) setRightSidebarOpen(false); }}
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
        className={`absolute right-0 z-20 transition-all duration-300 transform ${
          isRightSidebarOpen ? "translate-x-0" : "translate-x-full"
        } w-full md:w-auto md:top-0 md:bottom-0 bottom-0 top-auto max-h-[70vh] md:max-h-none rounded-t-2xl md:rounded-none`}
      >
        <div className="h-full flex flex-col">
          {/* Mobile drag handle */}
          <div className="md:hidden flex justify-center py-2 shrink-0">
            <div className="w-10 h-1 rounded-full bg-dark-100/50" />
          </div>
          <div className="flex-1 overflow-hidden">
            <ErrorBoundary name="Dashboard">
              <EvidencePanel />
              <div className="px-4 pb-4">
                <GroupImpactPanel />
              </div>
            </ErrorBoundary>
          </div>
        </div>
      </div>

      {/* Toggle Right Sidebar Button (desktop) */}
      <button
        onClick={() => { setRightSidebarOpen(!isRightSidebarOpen); if (!isRightSidebarOpen) setLeftSidebarOpen(false); }}
        className={`hidden md:flex absolute top-1/2 -translate-y-1/2 z-30 h-14 w-5 items-center justify-center rounded-l-xl border border-r-0 border-dark-100/50 bg-dark-200/90 text-gray-400 hover:text-white backdrop-blur-md shadow-lg transition-all ${
          isRightSidebarOpen ? "right-[420px]" : "right-0"
        }`}
        title={isRightSidebarOpen ? "Hide evidence panel" : "Show evidence panel"}
      >
        <span className="text-[10px] font-bold font-mono">
          {isRightSidebarOpen ? "▶" : "◀"}
        </span>
      </button>

      {/* Mobile Bottom Sheet Button for Evidence Panel */}
      <button
        onClick={() => { setRightSidebarOpen(!isRightSidebarOpen); if (!isRightSidebarOpen) setLeftSidebarOpen(false); }}
        className="md:hidden absolute bottom-[180px] right-4 z-30 flex h-10 w-10 items-center justify-center rounded-full border border-dark-100/50 bg-dark-200/90 text-gray-400 hover:text-white backdrop-blur-md shadow-lg transition-all"
        aria-label="Toggle evidence panel"
        title="Toggle evidence panel"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </button>

      {/* 5. Drawing Tool Overlay */}
      <div className="absolute right-4 top-20 z-10">
        <ErrorBoundary name="DrawingTools">
          <DrawingToolbar />
        </ErrorBoundary>
      </div>

      <div className="absolute left-1/2 top-20 z-10 w-[min(92vw,560px)] -translate-x-1/2 pointer-events-none">
        <div className="pointer-events-auto">
          <ErrorBoundary name="DataFreshness">
            <DataFreshnessPanel />
          </ErrorBoundary>
        </div>
      </div>

      {/* 6. Dynamic Bottom Drawer overlay: Playback controls and detailed metrics */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 w-[calc(100%-2rem)] md:w-full max-w-4xl px-0 md:px-4">
        <div className="flex flex-col gap-2 rounded-xl border border-dark-100/50 bg-dark-200/85 backdrop-blur-md p-2.5 md:p-3.5 shadow-2xl">
          {/* Metrics summary pills (clickable to expand charts) & Scrubber play block */}
          <ErrorBoundary name="Dashboard">
            <MetricPanel />
            <FrameScrubber />
          </ErrorBoundary>
        </div>
      </div>

      {/* 7. Loading Overlays */}
      <SimulationProgress />

      {/* 8. Keyboard Shortcuts Help Modal */}
      <KeyboardShortcutsHelp isOpen={showShortcuts} onClose={() => setShowShortcuts(false)} />
    </main>
  );
}
