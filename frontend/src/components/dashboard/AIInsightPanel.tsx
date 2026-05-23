"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { useSimulationStore } from "@/store/simulationStore";

export function AIInsightPanel() {
  const insight = useSimulationStore((s) => s.insight);
  const status = useSimulationStore((s) => s.status);
  const [collapsed, setCollapsed] = useState(false);

  if (status === "idle" && !insight) return null;

  const isStreaming = status === "running" && insight === null;

  return (
    <div className="bg-dark-200 border border-dark-100 rounded-lg overflow-hidden">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-dark-100 transition-colors"
      >
        <h3 className="text-sm font-semibold text-gray-200">AI Analysis</h3>
        <span className="text-gray-500 text-xs">
          {collapsed ? "Expand" : "Collapse"}
        </span>
      </button>

      {!collapsed && (
        <div className="px-4 pb-4 max-h-80 overflow-y-auto">
          {isStreaming && (
            <div className="flex items-center gap-2 text-sm text-yellow-400">
              <span className="animate-pulse">●</span>
              Generating analysis...
            </div>
          )}
          {insight && (
            <div className="prose prose-invert prose-sm max-w-none text-gray-300">
              <ReactMarkdown>{insight}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
