"use client";

import React from "react";
import { useSimulationStore } from "@/store/simulationStore";
import type { GroupImpact } from "@/types/simulation";

const GROUP_LABELS: Record<string, string> = {
  farmers: "Farmers",
  students: "Students",
  middle_class_families: "Middle Class",
  small_businesses: "Small Business",
  corporates: "Corporates",
  transport_sector: "Transport",
  government: "Government",
};

const GROUP_ICONS: Record<string, string> = {
  farmers: "🌾",
  students: "🎓",
  middle_class_families: "🏠",
  small_businesses: "🏪",
  corporates: "🏢",
  transport_sector: "🚛",
  government: "🏛️",
};

const SEVERITY_COLORS = {
  low: "border-emerald-500/30 bg-emerald-950/20 text-emerald-300",
  moderate: "border-amber-500/30 bg-amber-950/20 text-amber-300",
  high: "border-red-500/30 bg-red-950/20 text-red-300",
};

export const GroupImpactPanel = React.memo(function GroupImpactPanel() {
  const groupScores = useSimulationStore((s) => s.groupScores);
  const citizenSatisfaction = useSimulationStore((s) => s.citizenSatisfaction);

  if (groupScores.length === 0) return null;

  return (
    <div className="space-y-3">
      {/* Citizen Satisfaction Gauge */}
      {citizenSatisfaction !== null && (
        <div className="rounded-xl border border-dark-100/50 bg-dark-200/80 p-4 backdrop-blur-md">
          <div className="text-[9px] font-bold uppercase tracking-widest text-gray-500 mb-2">
            Citizen Satisfaction
          </div>
          <div className="flex items-center gap-3">
            <div className="text-3xl font-bold text-white">
              {citizenSatisfaction}
            </div>
            <div className="flex-1">
              <div className="h-2 rounded-full bg-dark-300 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    citizenSatisfaction >= 60
                      ? "bg-emerald-500"
                      : citizenSatisfaction >= 40
                        ? "bg-amber-500"
                        : "bg-red-500"
                  }`}
                  style={{ width: `${citizenSatisfaction}%` }}
                />
              </div>
              <div className="flex justify-between text-[9px] text-gray-600 mt-1">
                <span>0</span>
                <span>100</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Group Cards */}
      <div className="grid grid-cols-2 gap-2">
        {groupScores.map((group) => (
          <GroupCard key={group.name} group={group} />
        ))}
      </div>
    </div>
  );
});

function GroupCard({ group }: { group: GroupImpact }) {
  const label = GROUP_LABELS[group.name] ?? group.name;
  const icon = GROUP_ICONS[group.name] ?? "📊";
  const colorClass = SEVERITY_COLORS[group.severity];

  return (
    <div className={`rounded-xl border p-3 backdrop-blur-md ${colorClass}`}>
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-sm">{icon}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider">{label}</span>
      </div>
      <div className="space-y-1 text-[10px]">
        <MetricRow label="Purchasing Power" value={group.purchasing_power} />
        <MetricRow label="Income" value={group.income_stability} />
        <MetricRow label="Expenses" value={group.expense_pressure} inverted />
        <MetricRow label="Housing" value={group.housing_impact} />
        <MetricRow label="Jobs" value={-group.employment_impact} />
      </div>
    </div>
  );
}

function MetricRow({
  label,
  value,
  inverted = false,
}: {
  label: string;
  value: number;
  inverted?: boolean;
}) {
  const isPositive = inverted ? value < 0 : value > 0;
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-500">{label}</span>
      <span className={`font-mono font-bold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
        {value > 0 ? "+" : ""}
        {value.toFixed(1)}%
      </span>
    </div>
  );
}
