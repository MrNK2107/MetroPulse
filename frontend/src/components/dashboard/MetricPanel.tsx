"use client";

import React, { useMemo } from "react";
import {
  Card,
  AreaChart,
  Title,
  Text,
} from "@tremor/react";
import { useSimulationStore } from "@/store/simulationStore";
import type { MetricKey, AggregateMetrics } from "@/types/simulation";

interface MetricChartProps {
  title: string;
  unit: string;
  dataKey: MetricKey;
  color: string;
  formatter: (value: number) => string;
  currentValue: number | null;
}

const CHART_CONFIGS: Omit<MetricChartProps, "currentValue">[] = [
  {
    title: "GDP Δ",
    unit: "Change from baseline",
    dataKey: "gdpDelta",
    color: "emerald",
    formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
  },
  {
    title: "Unemployment",
    unit: "Rate",
    dataKey: "unemploymentRate",
    color: "amber",
    formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
  },
  {
    title: "Real Estate Index",
    unit: "Relative value",
    dataKey: "realEstateIndex",
    color: "violet",
    formatter: (v: number) => v.toFixed(3),
  },
  {
    title: "Transit Congestion",
    unit: "Load factor",
    dataKey: "transitCongestion",
    color: "rose",
    formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
  },
  {
    title: "Informal Share",
    unit: "Employment mix",
    dataKey: "informalEmployment",
    color: "cyan",
    formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
  },
  {
    title: "Affordability",
    unit: "Housing index",
    dataKey: "housingAffordability",
    color: "indigo",
    formatter: (v: number) => v.toFixed(2),
  },
];

const MetricChart = React.memo(function MetricChart({ title, unit, dataKey, color, formatter, currentValue }: MetricChartProps) {
  const metrics = useSimulationStore((s) => s.metrics);

  const chartData = useMemo(() => {
    return metrics.map((m, i) => ({
      month: `M${i + 1}`,
      value: m[dataKey],
    }));
  }, [metrics, dataKey]);

  return (
    <Card className="bg-dark-300/40 border-dark-100/50 p-4">
      <div className="flex items-center justify-between">
        <div>
          <Title className="text-gray-300 text-xs font-semibold uppercase tracking-wider">{title}</Title>
          <Text className="text-gray-500 text-[10px]">{unit}</Text>
        </div>
        {currentValue !== null && (
          <span className={`text-xs font-mono font-bold ${
            dataKey === "gdpDelta"
              ? (currentValue >= 0 ? "text-emerald-400" : "text-red-400")
              : dataKey === "unemploymentRate"
                ? "text-amber-400"
                : dataKey === "realEstateIndex"
                  ? "text-violet-400"
                  : dataKey === "transitCongestion"
                    ? "text-rose-400"
                    : dataKey === "informalEmployment"
                      ? "text-cyan-400"
                      : "text-indigo-400"
          }`}>
            {formatter(currentValue)}
          </span>
        )}
      </div>
      <AreaChart
        className="mt-4 h-24"
        data={chartData}
        index="month"
        categories={["value"]}
        colors={[color]}
        valueFormatter={formatter}
        showLegend={false}
        showGridLines={false}
        showXAxis={true}
        showYAxis={true}
        showAnimation={true}
        curveType="monotone"
        yAxisWidth={35}
      />
    </Card>
  );
});

export function MetricPanel() {
  const stage = useSimulationStore((s) => s.pipelineStage);
  const isRunning = stage === "simulating";
  const frames = useSimulationStore((s) => s.frames);
  const activeFrameIndex = useSimulationStore((s) => s.activeFrameIndex);
  const simulationId = useSimulationStore((s) => s.simulationId);
  const parsedScenario = useSimulationStore((s) => s.parsedScenario);
  const prediction = useSimulationStore((s) => s.prediction);
  const caseStudies = useSimulationStore((s) => s.caseStudies);
  const evidence = useSimulationStore((s) => s.evidence);
  const metrics = useSimulationStore((s) => s.metrics);

  const isBottomDrawerOpen = useSimulationStore((s) => s.isBottomDrawerOpen);
  const setBottomDrawerOpen = useSimulationStore((s) => s.setBottomDrawerOpen);

  const handleExport = () => {
    const data = {
      scenario: parsedScenario,
      prediction,
      frames,
      metrics,
      caseStudies,
      evidence,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `metropulse-${simulationId || "export"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const currentFrame =
    frames.length > 0 && activeFrameIndex >= 0
      ? frames[Math.min(activeFrameIndex, frames.length - 1)]
      : null;

  const currentMetrics = currentFrame?.metrics || null;
  const isDataAvailable = frames.length > 0;

  return (
    <div className="space-y-3 font-sans">
      {/* HUD Header & Summary Pills Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 select-none">
        <div className="flex items-center gap-2">
          <h2 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
            Key Timeline Metrics
          </h2>
          {isRunning && (
            <span className="text-[9px] font-bold bg-yellow-500/10 border border-yellow-500/25 text-yellow-500 px-1.5 py-0.5 rounded-full animate-pulse">
              LIVE
            </span>
          )}
        </div>

        {isDataAvailable && (
          <div className="flex gap-2">
            <button
              onClick={handleExport}
              className="text-[10px] font-bold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 border border-emerald-500/20 bg-emerald-950/20 px-2.5 py-1 rounded-lg transition-all"
            >
              Export JSON
            </button>
            <button
              onClick={() => setBottomDrawerOpen(!isBottomDrawerOpen)}
              className="text-[10px] font-bold text-blue-400 hover:text-blue-300 flex items-center gap-1 border border-blue-500/20 bg-blue-950/20 px-2.5 py-1 rounded-lg transition-all"
            >
              <span>{isBottomDrawerOpen ? "Hide Detailed Charts" : "Show Detailed Charts"}</span>
              <span>{isBottomDrawerOpen ? "▼" : "▲"}</span>
            </button>
          </div>
        )}
      </div>

      {/* Summary Pills Grid (Shows live current metrics) */}
      {!isDataAvailable ? (
        <div className="h-10 flex items-center justify-center border border-dashed border-dark-100/50 rounded-xl bg-dark-300/10 py-6">
          <Text className="text-gray-500 text-xs font-medium">Run a simulation prompt to inspect timeline metrics.</Text>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
          {CHART_CONFIGS.map((config) => {
            const rawVal = currentMetrics ? currentMetrics[config.dataKey] : null;
            const valStr = rawVal !== null ? config.formatter(rawVal) : "—";
            
            // Enforce unified semantic color-coding: green for growth/healthy, red for stress/drop, slate for stable
            let valColor = "text-gray-300";
            if (rawVal !== null) {
              if (config.dataKey === "gdpDelta") {
                valColor = rawVal >= 0 ? "text-emerald-400 font-bold" : "text-red-400 font-bold";
              } else if (config.dataKey === "unemploymentRate") {
                valColor = rawVal > 0.05 ? "text-red-400 font-bold" : rawVal < 0.045 ? "text-emerald-400 font-bold" : "text-gray-300 font-bold";
              } else if (config.dataKey === "realEstateIndex") {
                valColor = rawVal > 1.05 ? "text-emerald-400 font-bold" : rawVal < 0.95 ? "text-red-400 font-bold" : "text-gray-300 font-bold";
              } else if (config.dataKey === "transitCongestion") {
                valColor = rawVal > 0.40 ? "text-red-400 font-bold" : rawVal < 0.25 ? "text-emerald-400 font-bold" : "text-gray-300 font-bold";
              } else if (config.dataKey === "housingAffordability") {
                valColor = rawVal >= 1.0 ? "text-emerald-400 font-bold" : rawVal < 0.9 ? "text-red-400 font-bold" : "text-gray-300 font-bold";
              } else if (config.dataKey === "informalEmployment") {
                valColor = "text-sky-400 font-bold"; // Neutral informational blue
              }
            }

            return (
              <div
                key={config.dataKey}
                onClick={() => setBottomDrawerOpen(!isBottomDrawerOpen)}
                className="flex items-center justify-between rounded-xl border border-dark-100/30 bg-dark-300/40 px-3.5 h-12 cursor-pointer hover:border-blue-500/30 hover:bg-dark-300/60 transition-all select-none"
              >
                <div className="flex flex-col justify-center min-w-0">
                  <span className="text-[9px] font-bold text-gray-500 uppercase tracking-widest truncate">
                    {config.title.replace("Delta", "Δ")}
                  </span>
                  <span className="text-[8px] text-gray-600 font-mono truncate">{config.unit}</span>
                </div>
                <span className={`text-[11px] font-mono ${valColor} ml-2 shrink-0`}>{valStr}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Expandable detailed charts grid */}
      {isBottomDrawerOpen && isDataAvailable && currentMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-dark-100/30 animate-slide-up">
          {CHART_CONFIGS.map((config) => (
            <MetricChart
              key={config.dataKey}
              {...config}
              currentValue={currentMetrics[config.dataKey]}
            />
          ))}
        </div>
      )}
    </div>
  );
}
