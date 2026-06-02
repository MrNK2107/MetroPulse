"use client";

import React, { useMemo } from "react";
import {
  Card,
  AreaChart,
  Title,
  Text,
} from "@tremor/react";
import { useSimulationStore, selectCurrentFrame } from "@/store/simulationStore";
import type { AggregateMetrics } from "@/types/simulation";

/** Keys of AggregateMetrics that are always present (non-optional numbers). */
type RequiredMetricKey = {
  [K in keyof AggregateMetrics]-?: AggregateMetrics[K] extends number ? K : never
}[keyof AggregateMetrics];

interface MetricChartProps {
  title: string;
  unit: string;
  dataKey: RequiredMetricKey;
  color: string;
  formatter: (value: number) => string;
  currentValue: number | null;
  tooltip?: string;
  metadata?: { confidence: number; confidence_label: string; origin: string; sources: string[] };
}

const CHART_CONFIGS: Omit<MetricChartProps, "currentValue" | "metadata">[] = [
  {
    title: "GDP Δ",
    unit: "Change from baseline",
    dataKey: "gdpDelta",
    color: "emerald",
    formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
    tooltip: "GDP Δ: Change in city economic output. Positive = growth, negative = contraction. Values above 5% indicate significant expansion.",
  },
  {
    title: "Unemployment",
    unit: "Rate",
    dataKey: "unemploymentRate",
    color: "amber",
    formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
    tooltip: "Unemployment: Share of workforce actively seeking jobs. Below 6% is healthy; above 8% signals labor stress. Rising rates may indicate economic slowdown.",
  },
  {
    title: "Real Estate Index",
    unit: "Relative value",
    dataKey: "realEstateIndex",
    color: "violet",
    formatter: (v: number) => v.toFixed(3),
    tooltip: "Real Estate Index: Relative property value (1.0 = baseline). Above 1.05 = appreciating market; below 0.95 = declining values. Tracks commercial & residential.",
  },
  {
    title: "Transit Congestion",
    unit: "Load factor",
    dataKey: "transitCongestion",
    color: "rose",
    formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
    tooltip: "Transit Congestion: Road & public transport load. Below 25% = smooth flow; above 40% = significant delays. Affects commute times and productivity.",
  },
  {
    title: "Informal Share",
    unit: "Employment mix",
    dataKey: "informalEmployment",
    color: "cyan",
    formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
    tooltip: "Informal Share: Portion of workers in unregulated/informal jobs. Higher values suggest weaker labor protections and lower tax base. Purely informational metric.",
  },
  {
    title: "Affordability",
    unit: "Housing index",
    dataKey: "housingAffordability",
    color: "indigo",
    formatter: (v: number) => v.toFixed(2),
    tooltip: "Affordability: Ratio of median income to housing costs. Above 1.0 = affordable; below 0.9 = housing stress. Lower values mean less affordable housing.",
  },
];

const MetricChart = React.memo(function MetricChart({ title, unit, dataKey, color, formatter, currentValue, metadata }: MetricChartProps) {
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
          {metadata && (
            <Text className="text-gray-500 text-[10px]">
              Confidence: {metadata.confidence_label} · Origin: {metadata.origin.replace(/_/g, " ")}
            </Text>
          )}
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

interface AQIPillProps {
  value: number;
  isBottomDrawerOpen: boolean;
  setBottomDrawerOpen: (open: boolean) => void;
}

function AQIPill({ value, isBottomDrawerOpen, setBottomDrawerOpen }: AQIPillProps) {
  const aqiColor = value <= 100 ? "text-emerald-400 font-bold" : value <= 200 ? "text-amber-400 font-bold" : "text-red-400 font-bold";
  return (
    <button
      onClick={() => setBottomDrawerOpen(!isBottomDrawerOpen)}
      aria-label={`Air Quality Index: ${value.toFixed(0)}`}
      title="AQI: Air Quality Index (0–500 scale). 0–50 = Good, 51–100 = Moderate, 101–200 = Unhealthy for sensitive groups, 200+ = Unhealthy. Lower is better."
      className="flex items-center justify-between rounded-xl border border-dark-100/30 bg-dark-300/40 px-3.5 h-12 cursor-pointer hover:border-blue-500/30 hover:bg-dark-300/60 transition-all select-none text-left"
    >
      <div className="flex flex-col justify-center min-w-0">
        <span className="text-[9px] font-bold text-gray-500 uppercase tracking-widest truncate">AQI</span>
        <span className="text-[8px] text-gray-600 font-mono truncate">Air Quality Index</span>
      </div>
      <span className={`text-[11px] font-mono ${aqiColor} ml-2 shrink-0`}>{value.toFixed(0)}</span>
    </button>
  );
}

interface WaterStressPillProps {
  value: number;
  isBottomDrawerOpen: boolean;
  setBottomDrawerOpen: (open: boolean) => void;
}

function WaterStressPill({ value, isBottomDrawerOpen, setBottomDrawerOpen }: WaterStressPillProps) {
  const wsColor = value < 0.4 ? "text-blue-400 font-bold" : value < 0.7 ? "text-amber-400 font-bold" : "text-red-400 font-bold";
  return (
    <button
      onClick={() => setBottomDrawerOpen(!isBottomDrawerOpen)}
      aria-label={`Water Stress: ${(value * 100).toFixed(0)}%`}
      title="Water Stress: Ratio of water demand to supply. Below 40% = low stress, 40–70% = medium stress, above 70% = high stress. Higher means water scarcity risk."
      className="flex items-center justify-between rounded-xl border border-dark-100/30 bg-dark-300/40 px-3.5 h-12 cursor-pointer hover:border-blue-500/30 hover:bg-dark-300/60 transition-all select-none text-left"
    >
      <div className="flex flex-col justify-center min-w-0">
        <span className="text-[9px] font-bold text-gray-500 uppercase tracking-widest truncate">Water Stress</span>
        <span className="text-[8px] text-gray-600 font-mono truncate">Stress Index</span>
      </div>
      <span className={`text-[11px] font-mono ${wsColor} ml-2 shrink-0`}>{(value * 100).toFixed(0)}%</span>
    </button>
  );
}

/** Thresholds for semantic color-coding of metric pills */
const UNEMPLOYMENT_RED_THRESHOLD = 0.08;
const UNEMPLOYMENT_GREEN_THRESHOLD = 0.06;
const REAL_ESTATE_GREEN_THRESHOLD = 1.05;
const REAL_ESTATE_RED_THRESHOLD = 0.95;
const TRANSIT_RED_THRESHOLD = 0.40;
const TRANSIT_GREEN_THRESHOLD = 0.25;
const AFFORDABILITY_GREEN_THRESHOLD = 1.0;
const AFFORDABILITY_RED_THRESHOLD = 0.9;

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
  const snapshot = useSimulationStore((s) => s.snapshot);
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
      snapshotId: snapshot?.id ?? frames[frames.length - 1]?.proof?.snapshotId ?? null,
      source_manifest: snapshot?.sourceManifest ?? frames[frames.length - 1]?.proof?.dataSources ?? {},
      quality_score: snapshot?.qualityScore ?? frames[frames.length - 1]?.proof?.qualityScore ?? 0,
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

  const currentFrame = useSimulationStore(selectCurrentFrame);

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
              RUNNING
            </span>
          )}
          <span className={`text-[9px] font-bold border px-1.5 py-0.5 rounded-full ${
            snapshot?.status === "fresh"
              ? "bg-emerald-500/10 border-emerald-500/25 text-emerald-400"
              : snapshot?.status === "degraded"
                ? "bg-amber-500/10 border-amber-500/25 text-amber-400"
                : "bg-sky-500/10 border-sky-500/25 text-sky-400"
          }`}>
            {snapshot?.status === "fresh" ? "DATA-INFORMED" : snapshot?.status === "degraded" ? "PARTIAL CONTEXT" : "ESTIMATED"}
          </span>
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

      {/* Summary Pills Grid (Shows current scenario-estimate metrics) */}
      {!isDataAvailable ? (
        isRunning ? (
          <div className="grid grid-cols-2 md:grid-cols-6 gap-2 animate-pulse">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-dark-100/20 bg-dark-300/30 px-3.5 h-12 flex items-center justify-between">
                <div className="space-y-1.5">
                  <div className="h-2 w-10 bg-dark-100/50 rounded" />
                  <div className="h-1.5 w-14 bg-dark-100/30 rounded" />
                </div>
                <div className="h-3 w-8 bg-dark-100/50 rounded" />
              </div>
            ))}
          </div>
        ) : (
          <div className="h-10 flex items-center justify-center border border-dashed border-dark-100/50 rounded-xl bg-dark-300/10 py-6">
            <Text className="text-gray-500 text-xs font-medium">Run a simulation prompt to inspect timeline metrics.</Text>
          </div>
        )
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
          {CHART_CONFIGS.map((config) => {
            const rawVal = currentMetrics ? currentMetrics[config.dataKey] : null;
            const valStr = rawVal !== null ? config.formatter(rawVal) : "—";
            const metadata = currentFrame?.metric_metadata?.[config.dataKey];
            
            // Enforce unified semantic color-coding: green for growth/healthy, red for stress/drop, slate for stable
            let valColor = "text-gray-300";
            if (rawVal !== null) {
              if (config.dataKey === "gdpDelta") {
                valColor = rawVal >= 0 ? "text-emerald-400 font-bold" : "text-red-400 font-bold";
              } else if (config.dataKey === "unemploymentRate") {
                valColor = rawVal >= UNEMPLOYMENT_RED_THRESHOLD ? "text-red-400 font-bold" : rawVal < UNEMPLOYMENT_GREEN_THRESHOLD ? "text-emerald-400 font-bold" : "text-amber-400 font-bold";
              } else if (config.dataKey === "realEstateIndex") {
                valColor = rawVal > REAL_ESTATE_GREEN_THRESHOLD ? "text-emerald-400 font-bold" : rawVal < REAL_ESTATE_RED_THRESHOLD ? "text-red-400 font-bold" : "text-gray-300 font-bold";
              } else if (config.dataKey === "transitCongestion") {
                valColor = rawVal > TRANSIT_RED_THRESHOLD ? "text-red-400 font-bold" : rawVal < TRANSIT_GREEN_THRESHOLD ? "text-emerald-400 font-bold" : "text-gray-300 font-bold";
              } else if (config.dataKey === "housingAffordability") {
                valColor = rawVal >= AFFORDABILITY_GREEN_THRESHOLD ? "text-emerald-400 font-bold" : rawVal < AFFORDABILITY_RED_THRESHOLD ? "text-red-400 font-bold" : "text-gray-300 font-bold";
              } else if (config.dataKey === "informalEmployment") {
                valColor = "text-sky-400 font-bold"; // Neutral informational blue
              }
            }

            return (
              <button
                key={config.dataKey}
                onClick={() => setBottomDrawerOpen(!isBottomDrawerOpen)}
                aria-label={`${config.title}: ${valStr}`}
                title={config.tooltip}
                className="flex items-center justify-between rounded-xl border border-dark-100/30 bg-dark-300/40 px-3.5 h-12 cursor-pointer hover:border-blue-500/30 hover:bg-dark-300/60 transition-all select-none text-left"
              >
                <div className="flex flex-col justify-center min-w-0">
                  <span className="text-[9px] font-bold text-gray-500 uppercase tracking-widest truncate">
                    {config.title.replace("Delta", "Δ")}
                  </span>
                  <span className="text-[8px] text-gray-600 font-mono truncate">{config.unit}</span>
                </div>
                <span className={`text-[11px] font-mono ${valColor} ml-2 shrink-0`}>{valStr}</span>
                {metadata && (
                  <span
                    className="ml-2 flex flex-col items-end gap-0.5"
                    title="Confidence reflects input data quality, evidence coverage, and model assumptions. It is not a probability."
                  >
                    <span className="rounded-full border border-dark-100/40 bg-dark-300/60 px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider text-gray-400">
                      {metadata.confidence_label}
                    </span>
                    <span className="text-[7px] text-gray-600 font-mono">
                      {metadata.origin.replace(/_/g, " ")}
                    </span>
                  </span>
                )}
              </button>
            );
          })}
          {currentMetrics?.airQualityIndex !== undefined && (
            <AQIPill
              value={currentMetrics.airQualityIndex}
              isBottomDrawerOpen={isBottomDrawerOpen}
              setBottomDrawerOpen={setBottomDrawerOpen}
            />
          )}
          {currentMetrics?.waterStressIndex !== undefined && (
            <WaterStressPill
              value={currentMetrics.waterStressIndex}
              isBottomDrawerOpen={isBottomDrawerOpen}
              setBottomDrawerOpen={setBottomDrawerOpen}
            />
          )}
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
              metadata={currentFrame?.metric_metadata?.[config.dataKey]}
            />
          ))}
        </div>
      )}
    </div>
  );
}
