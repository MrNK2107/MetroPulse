"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSimulationStore } from "@/store/simulationStore";

let katexModule: typeof import("katex") | null = null;
function getKatex() {
  if (!katexModule) {
    katexModule = require("katex");
    require("katex/dist/katex.min.css");
  }
  return katexModule;
}

type ActiveTab = "report" | "cases" | "proof";

function LaTeX({ math, block = false }: { math: string; block?: boolean }) {
  try {
    const html = getKatex()!.renderToString(math, {
      displayMode: block,
      throwOnError: false,
    });
    return <span dangerouslySetInnerHTML={{ __html: html }} className={block ? "block my-2" : "inline-block"} />;
  } catch {
    return <span className="font-mono">{math}</span>;
  }
}

export function EvidencePanel() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("report");
  const evidence = useSimulationStore((s) => s.evidence);
  const caseStudies = useSimulationStore((s) => s.caseStudies);
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);
  const currentFrame = useSimulationStore((s) => {
    if (s.frames.length === 0) return null;
    const idx = s.activeFrameIndex >= 0 ? s.activeFrameIndex : s.frames.length - 1;
    return s.frames[Math.min(idx, s.frames.length - 1)];
  });

  const isDataAvailable = Boolean(evidence || currentFrame);
  const activeLoop = currentFrame?.activeLoop ?? (evidence?.proof?.activeEffects?.join(" -> ") || "complete");

  // Streaming text reveal for Report tab
  const [visibleWords, setVisibleWords] = useState(0);
  const totalWordsRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!evidence?.markdown) {
      setVisibleWords(0);
      return;
    }
    const words = evidence.markdown.split(/\s+/);
    totalWordsRef.current = words.length;
    setVisibleWords(0);

    // Fast reveal: ~15ms per word
    intervalRef.current = setInterval(() => {
      setVisibleWords((prev) => {
        if (prev >= totalWordsRef.current) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          return prev;
        }
        return prev + 3; // reveal 3 words at a time for speed
      });
    }, 15);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [evidence?.markdown]);

  // Pre-process markdown to clean literal "Delta/delta" words and set up inline LaTeX formatting
  const processedMarkdown = useMemo(() => {
    if (!evidence?.markdown) return "";
    const raw = evidence.markdown
      .replace(/\bDelta K_sector = monthly_rate \* sector_weight \* K\b/g, "\\Delta K_{sector} = \\text{monthly\\_rate} \\times \\text{sector\\_weight} \\times K")
      .replace(/\bDelta\b/g, "Δ")
      .replace(/\bdelta\b/g, "Δ");
    // Apply streaming reveal: truncate to visible words
    if (visibleWords > 0 && visibleWords < totalWordsRef.current) {
      const words = raw.split(/\s+/);
      return words.slice(0, visibleWords).join(" ");
    }
    return raw;
  }, [evidence?.markdown, visibleWords]);

  return (
    <aside className="w-[420px] flex flex-col border-l border-dark-100/50 bg-dark-200/95 backdrop-blur-md h-full shadow-2xl">
      {/* Panel Header */}
      <div className="border-b border-dark-100/40 p-5 bg-dark-300/40 select-none">
        <h2 className="text-sm font-bold uppercase tracking-widest text-gray-100">
          Evidence & Audit
        </h2>
        <p className="mt-1 text-[10px] text-gray-500 font-medium uppercase tracking-wider">
          Simulation analysis, precedence, and math checks
        </p>
      </div>

      {!isDataAvailable ? (
        // Empty State
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center gap-3">
          <div className="w-12 h-12 rounded-full bg-dark-300/80 border border-dark-100/60 flex items-center justify-center text-gray-500 shadow-inner">
            🔍
          </div>
          <div>
            <h3 className="text-xs font-bold text-gray-300 uppercase tracking-wider">No Simulation Audits</h3>
            <p className="mt-1 text-[11px] text-gray-500 max-w-[260px] leading-[1.5]">
              Enter a scenario prompt on the left sidebar and trigger a simulation run to generate reports.
            </p>
          </div>
        </div>
      ) : (
        // Tabbed Panel
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs Navigation */}
          <div className="flex border-b border-dark-100/30 bg-dark-300/20 p-2 gap-1 select-none">
            <button
              onClick={() => setActiveTab("report")}
              className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all ${
                activeTab === "report"
                  ? "bg-blue-600/95 text-white shadow-md shadow-blue-500/10"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
              }`}
            >
              Report
            </button>
            <button
              onClick={() => setActiveTab("cases")}
              className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                activeTab === "cases"
                  ? "bg-blue-600/95 text-white shadow-md shadow-blue-500/10"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
              }`}
            >
              <span>Precedents</span>
              {caseStudies.length > 0 && (
                <span className="bg-dark-100/80 text-[8px] font-mono px-1.5 py-0.5 rounded-full text-gray-300 font-bold border border-dark-100">
                  {caseStudies.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("proof")}
              className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all ${
                activeTab === "proof"
                  ? "bg-blue-600/95 text-white shadow-md shadow-blue-500/10"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
              }`}
            >
              Math Proof
            </button>
          </div>

          {/* Tab Content Area */}
          <div className="flex-1 overflow-y-auto p-5 no-scrollbar">
            {pipelineStage === "retrieving" || pipelineStage === "synthesizing" ? (
              // Loading audit state
              <div className="space-y-4 animate-pulse pt-2">
                <div className="h-4 bg-dark-300 rounded-lg w-3/4"></div>
                <div className="space-y-2.5">
                  <div className="h-3 bg-dark-300 rounded-lg w-full"></div>
                  <div className="h-3 bg-dark-300 rounded-lg w-5/6"></div>
                  <div className="h-3 bg-dark-300 rounded-lg w-4/5"></div>
                </div>
                <div className="h-16 bg-dark-300 rounded-xl w-full mt-6"></div>
              </div>
            ) : (
              <>
                {/* Tab: Report */}
                {activeTab === "report" && (
                  <div className="space-y-4">
                    {evidence ? (
                      <article className="font-sans text-gray-300 leading-[1.5]">
                        {/* Blinking cursor while streaming */}
                        {visibleWords > 0 && visibleWords < totalWordsRef.current && (
                          <span className="inline-block w-1.5 h-3 bg-blue-400 animate-pulse ml-0.5 align-middle" />
                        )}
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h2: ({ node, ...props }) => (
                              <h2 className="text-xs font-bold text-blue-400 uppercase tracking-widest border-b border-dark-100/30 pb-1.5 mt-5 mb-2.5" {...props} />
                            ),
                            h3: ({ node, ...props }) => (
                              <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider mt-4 mb-2" {...props} />
                            ),
                            p: ({ node, ...props }) => (
                              <p className="text-xs leading-[1.5] text-gray-400 mb-3 font-medium" {...props} />
                            ),
                            ul: ({ node, ...props }) => (
                              <ul className="list-disc pl-4 space-y-1.5 text-xs text-gray-400 mb-4 leading-[1.5]" {...props} />
                            ),
                            ol: ({ node, ...props }) => (
                              <ol className="list-decimal pl-4 space-y-1.5 text-xs text-gray-400 mb-4 leading-[1.5]" {...props} />
                            ),
                            li: ({ node, ...props }) => <li className="pl-0.5" {...props} />,
                            a: ({ node, ...props }) => (
                              <a className="text-blue-400 underline hover:text-blue-300 font-bold" {...props} />
                            ),
                            table: ({ node, ...props }) => (
                              <div className="overflow-x-auto my-4 rounded-xl border border-dark-100/40 bg-dark-300/10">
                                <table className="min-w-full divide-y divide-dark-100/30 text-xs" {...props} />
                              </div>
                            ),
                            thead: ({ node, ...props }) => <thead className="bg-dark-300/60" {...props} />,
                            tbody: ({ node, ...props }) => <tbody className="divide-y divide-dark-100/20" {...props} />,
                            tr: ({ node, ...props }) => <tr className="even:bg-dark-300/30 odd:bg-transparent" {...props} />,
                            th: ({ node, ...props }) => (
                              <th className="px-4 py-2.5 text-left font-bold text-[9px] text-gray-300 uppercase tracking-wider" {...props} />
                            ),
                            td: ({ node, ...props }) => <td className="px-4 py-2.5 text-gray-400 font-medium font-sans text-xs" {...props} />,
                            blockquote: ({ node, ...props }) => (
                              <blockquote className="border-l-2 border-blue-500 bg-blue-950/20 rounded-r-lg px-3 py-2.5 text-xs text-blue-200 my-4 leading-[1.5] font-sans" {...props} />
                            ),
                            code: ({ node, className, children, ...props }) => {
                              const codeString = String(children).trim();
                              // Intercept text formulas and typeset via KaTeX
                              if (codeString.includes("\\Delta") || codeString.includes("Delta") || codeString.includes("K_sector") || codeString.includes("monthly_rate")) {
                                const cleanMath = codeString
                                  .replace(/Delta/g, "\\Delta")
                                  .replace("Delta K_sector = monthly_rate * sector_weight * K", "\\Delta K_{sector} = \\text{monthly\\_rate} \\times \\text{sector\\_weight} \\times K");
                                return <LaTeX math={cleanMath} block={false} />;
                              }
                              return <code className={className} {...props}>{children}</code>;
                            }
                          }}
                        >
                          {processedMarkdown}
                        </ReactMarkdown>
                      </article>
                    ) : (
                      <div className="rounded-xl border border-dark-100/60 bg-dark-300/40 p-4">
                        <p className="text-xs text-gray-300 leading-[1.5]">Run the simulation to generate the final analytical report.</p>
                        <p className="mt-2 text-[10px] text-gray-500 leading-[1.5]">
                          Once the month-by-month animations conclude, the synthetic AI evidence and confirmation report will load here.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Tab: Precedent Case Studies */}
                {activeTab === "cases" && (
                  <div className="space-y-3">
                    {caseStudies.length > 0 ? (
                      caseStudies.map((study) => (
                        <div key={study.id} className="rounded-xl border border-dark-100/50 bg-dark-300/30 p-4 hover:border-dark-100 transition-all select-none">
                          <div className="flex justify-between items-start gap-3 border-b border-dark-100/30 pb-2">
                            <h4 className="text-xs font-bold text-gray-200">
                              {study.title}
                            </h4>
                            <span className="text-[9px] font-bold bg-dark-100 border border-dark-100 text-gray-400 px-2 py-0.5 rounded-full font-mono">
                              {study.year}
                            </span>
                          </div>
                          
                          <p className="mt-2 text-[11px] leading-[1.5] text-gray-400">
                            <span className="text-gray-300 font-semibold block mb-0.5">Precedent Details</span>
                            {study.description}
                          </p>
                          
                          {study.outcome && (
                            <p className="mt-2 text-[11px] leading-[1.5] text-emerald-400/90 bg-emerald-950/10 rounded-lg p-2 border border-emerald-500/10">
                              <span className="text-emerald-400 font-bold block mb-0.5 text-[9px] uppercase tracking-wider">Observed Outcome</span>
                              {study.outcome}
                            </p>
                          )}

                          <div className="mt-3 flex items-center justify-between text-[9px] uppercase font-bold tracking-wider pt-2 border-t border-dark-100/20 text-gray-500">
                            <span>Source: {study.source}</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-xl border border-dark-100/60 bg-dark-300/40 p-4 text-center py-8">
                        <span className="text-gray-600 text-2xl block mb-2">📁</span>
                        <p className="text-xs text-gray-400 font-semibold">No Case Studies Located</p>
                        <p className="mt-1 text-[10px] text-gray-500 max-w-[240px] mx-auto leading-[1.5]">
                          The keywords extracted from your prompt didn&apos;t trigger any historical precedents in the archive.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Tab: Math & Data Proof */}
                {activeTab === "proof" && (
                  <div className="space-y-4 leading-[1.5]">
                    {/* Active Loops Inspector */}
                    <div className="rounded-xl border border-dark-100/50 bg-dark-300/40 p-4">
                      <span className="text-[9px] font-bold uppercase tracking-widest text-blue-400 block mb-1">State Machine</span>
                      <h4 className="text-xs font-bold text-gray-200 mb-2">Simulation Loops Traversed</h4>
                      <div className="font-mono text-[10px] bg-dark-300/80 rounded-lg border border-dark-100/50 p-2.5 text-gray-300 select-all overflow-x-auto">
                        {activeLoop}
                      </div>
                    </div>

                    {/* Math Formulation */}
                    <div className="rounded-xl border border-dark-100/50 bg-dark-300/40 p-4">
                      <span className="text-[9px] font-bold uppercase tracking-widest text-violet-400 block mb-1">Algorithm</span>
                      <h4 className="text-xs font-bold text-gray-200 mb-2">Vector Update Formula</h4>
                      <p className="text-[11px] leading-[1.5] text-gray-400 mb-3">
                        {"Each H3 cell is updated monthly using NumPy array vector operations to compute employment pressure, $\\Delta K_{sector}$, and spatial decay."}
                      </p>
                      <div className="bg-dark-300/80 rounded-xl border border-dark-100/40 p-4 flex items-center justify-center select-all">
                        <LaTeX math="\Delta K_{sector} = \text{monthly\_rate} \times \text{sector\_weight} \times K" block={true} />
                      </div>
                      <p className="mt-3 text-[10px] text-gray-500 italic leading-[1.5]">
                        Note: Real estate index ($R$) and transit load ($T$) updates follow deterministic vector loops across neighboring cells.
                      </p>
                    </div>

                    {/* Data Audit trail */}
                    <div className="rounded-xl border border-dark-100/50 bg-dark-300/40 p-4">
                      <span className="text-[9px] font-bold uppercase tracking-widest text-amber-500 block mb-1">Data Source</span>
                      <h4 className="text-xs font-bold text-gray-200 mb-2">Baselines & Grid Density</h4>
                      <p className="text-[11px] leading-[1.5] text-gray-400 mb-3">
                        Baselines are built using city YAML configs, population sizes, distance-decay grids, and H3 coordinate layouts.
                      </p>
                      <div className="space-y-2 text-[11px]">
                        <div className="flex justify-between border-b border-dark-100/20 py-1.5">
                          <span className="text-gray-500">Data Reliability</span>
                          <span className="text-gray-300 font-semibold">{evidence?.proof?.dataQuality ? "Config Estimates" : "Fallback Estimates"}</span>
                        </div>
                        <div className="flex justify-between border-b border-dark-100/20 py-1.5">
                          <span className="text-gray-500">Active H3 Grid Cells</span>
                          <span className="text-gray-300 font-mono font-semibold">{evidence?.proof?.cellCount || currentFrame?.proof?.cellCount || 1415} cells</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
