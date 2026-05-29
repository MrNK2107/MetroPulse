"use client";

import { useMemo } from "react";
import { useSimulationStore } from "@/store/simulationStore";
import type { DataDomain, SourceStatus } from "@/types/simulation";

const DOMAIN_LABELS: Record<DataDomain, string> = {
  mobility: "Mobility",
  jobs: "Jobs",
  land_value: "Land",
  census: "Census",
  news: "News",
};

const ORDER: DataDomain[] = ["mobility", "jobs", "land_value", "census", "news"];

function statusClass(status: SourceStatus["freshness"] | undefined) {
  if (status === "fresh") return "border-emerald-500/30 bg-emerald-950/25 text-emerald-300";
  if (status === "stale") return "border-amber-500/30 bg-amber-950/25 text-amber-300";
  if (status === "demo") return "border-sky-500/30 bg-sky-950/25 text-sky-300";
  return "border-red-500/30 bg-red-950/25 text-red-300";
}

function compactDate(value: string | null | undefined) {
  if (!value) return "no timestamp";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "unknown";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function DataFreshnessPanel() {
  const snapshot = useSimulationStore((s) => s.snapshot);
  const currentFrame = useSimulationStore((s) => {
    if (s.frames.length === 0) return null;
    const idx = s.activeFrameIndex >= 0 ? s.activeFrameIndex : s.frames.length - 1;
    return s.frames[Math.min(idx, s.frames.length - 1)];
  });

  const manifest = useMemo(
    () => snapshot?.sourceManifest ?? currentFrame?.proof?.dataSources ?? {},
    [snapshot?.sourceManifest, currentFrame?.proof?.dataSources]
  );
  const mode = snapshot?.status ?? (currentFrame?.proof?.dataMode === "real_time" ? "fresh" : "demo");
  const quality = snapshot?.qualityScore ?? currentFrame?.proof?.qualityScore ?? 0;
  const overallConfidence = currentFrame?.proof?.overallConfidence;
  const confidenceLabel = overallConfidence != null
    ? overallConfidence >= 0.7 ? "High" : overallConfidence >= 0.4 ? "Medium" : "Low"
    : null;

  return (
    <div className="rounded-xl border border-dark-100/50 bg-dark-300/45 p-3 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[9px] font-bold uppercase tracking-widest text-gray-500">Simulation Trust</p>
          <p className="text-xs font-bold text-gray-200">
            {mode === "demo" ? "Synthetic Fallback" : mode === "degraded" ? "Data-Informed (Partial)" : "Data-Informed"}
          </p>
          {confidenceLabel && (
            <p className="text-[9px] text-gray-400 mt-0.5">
              Confidence: {confidenceLabel} ({((overallConfidence ?? 0) * 100).toFixed(0)}%)
            </p>
          )}
          <p className="text-[8px] text-gray-500 mt-0.5">
            Confidence reflects data quality, evidence coverage, and assumptions; it is not probability.
          </p>
        </div>
        <span className={`rounded-full border px-2 py-1 text-[9px] font-bold uppercase tracking-wider ${statusClass(mode === "demo" ? "demo" : mode === "degraded" ? "stale" : "fresh")}`}>
          {(quality * 100).toFixed(0)}%
        </span>
      </div>
      <div className="mt-3 grid grid-cols-5 gap-1.5">
        {ORDER.map((domain) => {
          const source = manifest[domain];
          return (
            <div
              key={domain}
              className={`min-w-0 rounded-lg border px-2 py-1.5 ${statusClass(source?.freshness)}`}
              title={`${source?.source ?? "No source"} - ${source?.notes ?? ""}`}
            >
              <p className="truncate text-[8px] font-bold uppercase tracking-wider">{DOMAIN_LABELS[domain]}</p>
              <p className="truncate text-[8px] opacity-80">{source?.freshness ?? "missing"}</p>
              <p className="truncate text-[8px] opacity-70">{compactDate(source?.observed_at)}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
