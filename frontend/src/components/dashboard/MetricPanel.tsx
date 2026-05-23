"use client";

import { useMemo } from "react";
import {
  Card,
  AreaChart,
  Title,
  Text,
} from "@tremor/react";
import { useSimulationStore } from "@/store/simulationStore";

interface MetricChartProps {
  title: string;
  unit: string;
  dataKey: keyof typeof import("@/types/simulation").AggregateMetrics;
  color: string;
  formatter?: (value: number) => string;
}

const CHART_CONFIGS: MetricChartProps[] = [
  {
    title: "GDP Delta",
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
];

function MetricChart({ title, unit, dataKey, color, formatter }: MetricChartProps) {
  const metrics = useSimulationStore((s) => s.metrics);
  const status = useSimulationStore((s) => s.status);

  const chartData = useMemo(() => {
    return metrics.map((m, i) => ({
      month: `M${i + 1}`,
      value: m[dataKey] as number,
    }));
  }, [metrics, dataKey]);

  const isEmpty = chartData.length === 0;

  return (
    <Card className="bg-dark-200 border-dark-100">
      <Title className="text-gray-200 text-sm">{title}</Title>
      <Text className="text-gray-500 text-xs">{unit}</Text>
      {isEmpty ? (
        <div className="h-40 flex items-center justify-center">
          <Text className="text-gray-600 text-xs">No data yet</Text>
        </div>
      ) : (
        <AreaChart
          className="mt-2 h-40"
          data={chartData}
          index="month"
          categories={["value"]}
          colors={[color]}
          valueFormatter={formatter ?? ((v: number) => String(v))}
          showLegend={false}
          showGridLines={false}
          showAnimation
          curveType="monotone"
        />
      )}
    </Card>
  );
}

export function MetricPanel() {
  const status = useSimulationStore((s) => s.status);
  const isRunning = status === "running";

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
          Metrics
        </h2>
        {isRunning && (
          <span className="text-xs text-yellow-400 animate-pulse">LIVE</span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3">
        {CHART_CONFIGS.map((config) => (
          <MetricChart key={config.dataKey} {...config} />
        ))}
      </div>
    </div>
  );
}
