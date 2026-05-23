"use client";

import dynamic from "next/dynamic";
import { ParameterPanel } from "@/components/controls/ParameterPanel";
import { MetricPanel } from "@/components/dashboard/MetricPanel";
import { AIInsightPanel } from "@/components/dashboard/AIInsightPanel";
import { LoadingOverlay } from "@/components/shared/LoadingOverlay";

const MapViewport = dynamic(
  () => import("@/components/map/MapViewport").then((m) => ({ default: m.MapViewport })),
  { ssr: false }
);

const DrawingToolbar = dynamic(
  () => import("@/components/map/DrawingToolbar").then((m) => ({ default: m.DrawingToolbar })),
  { ssr: false }
);

export default function Home() {
  return (
    <div className="flex h-screen w-screen overflow-hidden">
      <ParameterPanel />

      <div className="flex-1 flex flex-col relative">
        <div className="flex-1 relative">
          <MapViewport />
          <DrawingToolbar />
          <LoadingOverlay />
        </div>

        <div className="h-64 bg-dark-300 border-t border-dark-100 overflow-y-auto p-4">
          <div className="max-w-5xl mx-auto space-y-4">
            <MetricPanel />
            <AIInsightPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
