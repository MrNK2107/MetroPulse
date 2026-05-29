"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSimulationStore } from "@/store/simulationStore";
import { SECTOR_LABELS } from "@/types/simulation";
import type { SectorImpact, TranslationResult } from "@/types/simulation";

let katexModule: typeof import("katex") | null = null;
function getKatex() {
  if (!katexModule) {
    katexModule = require("katex");
    require("katex/dist/katex.min.css");
  }
  return katexModule;
}

type ActiveTab = "simple" | "detailed" | "cases" | "technical";

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

function AssumptionsList({ assumptions }: { assumptions: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-950/10">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-left"
      >
        <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
          Assumptions ({assumptions.length})
        </span>
        <span className="text-amber-400 text-xs">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <ul className="px-4 pb-3 space-y-1.5">
          {assumptions.map((a, i) => (
            <li key={i} className="text-[11px] text-amber-200/80 leading-[1.5] pl-2 border-l border-amber-500/30">
              {a}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function EvidencePanel() {
  const evidence = useSimulationStore((s) => s.evidence);
  const caseStudies = useSimulationStore((s) => s.caseStudies);
  const prediction = useSimulationStore((s) => s.prediction);
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);
  const currentFrame = useSimulationStore((s) => {
    if (s.frames.length === 0) return null;
    const idx = s.activeFrameIndex >= 0 ? s.activeFrameIndex : s.frames.length - 1;
    return s.frames[Math.min(idx, s.frames.length - 1)];
  });

  const hasSimpleView = Boolean(evidence?.translation?.sector_impacts?.length);
  const [activeTab, setActiveTab] = useState<ActiveTab>(hasSimpleView ? "simple" : "detailed");

  const isDataAvailable = Boolean(evidence || currentFrame);
  const activeLoop = currentFrame?.activeLoop ?? (evidence?.proof?.activeEffects?.join(" -> ") || "complete");
  const dataSources = currentFrame?.proof?.dataSources ?? evidence?.proof?.dataSources ?? {};
  const caseRetrieval = evidence?.case_retrieval;

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
    
    let raw = evidence.markdown;
    
    // Normalize and wrap the formula in backticks if it wasn't already
    raw = raw.replace(
      /(?<!`)(?:\\Delta|Delta)\s*K_sector\s*=\s*monthly_rate\s*\*\s*sector_weight\s*\*\s*K(?!`)/g,
      "`\\Delta K_{sector} = \\text{monthly\\_rate} \\times \\text{sector\\_weight} \\times K`"
    );
    
    // Extract code blocks temporarily to avoid replacing content inside math LaTeX equations
    const blocks: string[] = [];
    raw = raw.replace(/`[^`]+`/g, (match) => {
      blocks.push(match);
      return `__CODE_BLOCK_${blocks.length - 1}__`;
    });
    
    // Replace Delta/delta in plain text
    raw = raw.replace(/\bDelta\b/g, "Δ")
             .replace(/\bdelta\b/g, "Δ");
             
    // Restore code blocks
    raw = raw.replace(/__CODE_BLOCK_(\d+)__/g, (_, id) => blocks[parseInt(id, 10)]);

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
            {hasSimpleView && (
              <button
                onClick={() => setActiveTab("simple")}
                className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                  activeTab === "simple"
                    ? "bg-emerald-600/95 text-white shadow-md shadow-emerald-500/10"
                    : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
                }`}
              >
                <span>Simple</span>
                <span className="bg-emerald-500/30 text-[7px] font-mono px-1.5 py-0.5 rounded-full text-emerald-300 font-bold border border-emerald-500/30">
                  RECOMMENDED
                </span>
              </button>
            )}
            <button
              onClick={() => setActiveTab("detailed")}
              className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all ${
                activeTab === "detailed"
                  ? "bg-blue-600/95 text-white shadow-md shadow-blue-500/10"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
              }`}
            >
              Detailed
            </button>
            <button
              onClick={() => setActiveTab("cases")}
              className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                activeTab === "cases"
                  ? "bg-blue-600/95 text-white shadow-md shadow-blue-500/10"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
              }`}
            >
              <span>Cases</span>
              {caseStudies.length > 0 && (
                <span className="bg-dark-100/80 text-[8px] font-mono px-1.5 py-0.5 rounded-full text-gray-300 font-bold border border-dark-100">
                  {caseStudies.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("technical")}
              className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all ${
                activeTab === "technical"
                  ? "bg-blue-600/95 text-white shadow-md shadow-blue-500/10"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
              }`}
            >
              Technical
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
                {/* Tab: Simple (plain-language view) */}
                {activeTab === "simple" && evidence?.translation && (
                  <div className="space-y-4">
                    {/* Hero headline */}
                    <div className={`rounded-xl border p-4 ${
                      evidence.translation.overall_verdict.includes("positive")
                        ? "border-emerald-500/30 bg-emerald-950/15"
                        : evidence.translation.overall_verdict.includes("negative")
                        ? "border-red-500/30 bg-red-950/15"
                        : "border-amber-500/30 bg-amber-950/15"
                    }`}>
                      <p className="text-sm font-bold text-gray-100 leading-[1.5]">
                        {evidence.translation.headline}
                      </p>
                      <p className="mt-1 text-[10px] text-gray-400 italic">
                        {evidence.translation.overall_verdict}
                      </p>
                    </div>

                    {/* Sector impact cards */}
                    {evidence.translation.sector_impacts.slice(0, 3).map((impact) => (
                      <div key={impact.sector} className="rounded-xl border border-dark-100/50 bg-dark-300/30 p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                            impact.direction === "positive"
                              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                              : "bg-red-500/20 text-red-400 border border-red-500/30"
                          }`}>
                            {impact.delta_pct > 0 ? "+" : ""}{impact.delta_pct.toFixed(0)}%
                          </span>
                          <span className="text-xs font-bold text-gray-200">{impact.headline}</span>
                        </div>
                        <p className="text-xs text-gray-200 font-semibold leading-[1.5] mb-1.5">
                          {impact.person_example}
                        </p>
                        <p className="text-[11px] text-gray-400 leading-[1.5]">
                          {impact.city_wide}
                        </p>
                      </div>
                    ))}

                    {/* Takeaways */}
                    {evidence.translation.takeaways.length > 0 && (
                      <div className="rounded-xl border border-blue-500/20 bg-blue-950/10 p-4">
                        <h4 className="text-[10px] font-bold uppercase tracking-wider text-blue-400 mb-2.5">
                          What this means for you
                        </h4>
                        <ol className="space-y-2">
                          {evidence.translation.takeaways.map((t, i) => (
                            <li key={i} className="text-xs text-gray-300 leading-[1.5] flex gap-2">
                              <span className="text-blue-400 font-bold shrink-0">{i + 1}.</span>
                              <span>{t}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}

                    {evidence.explainability && (
                      <div className="rounded-xl border border-dark-100/50 bg-dark-300/30 p-4">
                        <h4 className="text-[10px] font-bold uppercase tracking-wider text-blue-400 mb-2.5">
                          Why this result?
                        </h4>
                        <p className="text-xs text-gray-300 leading-[1.5] mb-3">
                          {evidence.explainability.summary}
                        </p>
                        <div className="space-y-2">
                          {evidence.explainability.top_drivers.slice(0, 3).map((driver) => (
                            <div key={driver.factor} className="flex justify-between gap-3 text-[11px] border-b border-dark-100/20 pb-1.5">
                              <span className="text-gray-400">{driver.factor}</span>
                              <span className="text-gray-300 font-mono">{driver.contribution}%</span>
                            </div>
                          ))}
                        </div>
                        <p className="mt-3 text-[10px] text-gray-500">
                          Confidence: {evidence.explainability.confidence_label} ({(evidence.explainability.confidence * 100).toFixed(0)}%)
                        </p>
                      </div>
                    )}

                    {/* GDP + Unemployment summary */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-xl border border-dark-100/50 bg-dark-300/30 p-3 text-center">
                        <p className="text-[9px] font-bold uppercase tracking-wider text-gray-500 mb-1">Economy</p>
                        <p className="text-xs font-bold text-gray-200">{evidence.translation.gdp_summary}</p>
                      </div>
                      <div className="rounded-xl border border-dark-100/50 bg-dark-300/30 p-3 text-center">
                        <p className="text-[9px] font-bold uppercase tracking-wider text-gray-500 mb-1">Jobs</p>
                        <p className="text-xs font-bold text-gray-200">{evidence.translation.unemployment_summary}</p>
                      </div>
                    </div>

                    {/* Driver breakdown */}
                    {evidence.explanation?.gdp_delta?.drivers && evidence.explanation.gdp_delta.drivers.length > 0 && (
                      <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-4">
                        <h4 className="text-[10px] font-bold uppercase tracking-wider text-amber-400 mb-2.5">
                          Main Drivers
                        </h4>
                        <div className="space-y-1.5">
                          {evidence.explanation?.gdp_delta?.drivers?.map((d, i) => (
                            <div key={i} className="flex items-center justify-between text-xs">
                              <span className="text-gray-300">{d.factor}</span>
                              {d.contribution_pct > 0 && (
                                <span className="text-amber-300 font-mono font-medium">{d.contribution_pct}%</span>
                              )}
                            </div>
                          ))}
                        </div>
                        {evidence.explanation?.gdp_delta?.confidence != null && (
                          <p className="mt-2 text-[10px] text-gray-400">
                            Confidence: {(evidence.explanation!.gdp_delta!.confidence! * 100).toFixed(0)}%
                            {evidence.explanation!.gdp_delta!.confidence! < 0.5
                              ? " — model-generated estimate, interpret as directional"
                              : evidence.explanation!.gdp_delta!.confidence! < 0.7
                              ? " — based on estimated baselines"
                              : " — based on measured data"}
                          </p>
                        )}
                        <p className="mt-1.5 text-[9px] text-gray-500 italic">
                          This result is a model estimate for scenario exploration, not a prediction.
                        </p>
                      </div>
                    )}

                    {/* Disclaimer */}
                    <p className="text-[9px] text-gray-500 italic text-center leading-[1.5]">
                      Scenario estimates using city baselines, evidence retrieval, and contextual signals. Use for exploration, not certainty.
                    </p>

                    {/* How MetroPulse Works */}
                    <details className="rounded-xl border border-dark-100/30 bg-dark-300/20 p-3 text-[10px] text-gray-400">
                      <summary className="cursor-pointer font-bold text-gray-300 uppercase tracking-wider text-[9px]">
                        How MetroPulse Works
                      </summary>
                      <div className="mt-2 space-y-1.5 leading-relaxed">
                        <p><strong className="text-gray-300">Real context:</strong> News and public web signals can adjust bounded model modifiers when available.</p>
                        <p><strong className="text-gray-300">Estimated baselines:</strong> City population, GDP, employment, and sector weights come from configured city baselines.</p>
                        <p><strong className="text-gray-300">Synthetic layers:</strong> Cell-level spatial distribution uses urban anchors, H3 geometry, and transparent heuristics.</p>
                        <p><strong className="text-gray-300">Confidence:</strong> Reflects input quality, evidence coverage, and model assumptions. It is not probability.</p>
                        <p><strong className="text-gray-300">Limitations:</strong> Use for directional scenario exploration, not quantitative certainty or decision-grade forecasts.</p>
                      </div>
                    </details>
                  </div>
                )}

                {/* Tab: Detailed (original report) */}
                {activeTab === "detailed" && (
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
                              // Intercept math/formulas and typeset via KaTeX
                              if (
                                codeString.includes("\\Delta") ||
                                codeString.includes("Delta") ||
                                codeString.includes("K_") ||
                                codeString.includes("monthly") ||
                                codeString.includes("sector_")
                              ) {
                                const cleanMath = codeString
                                  .replace(/Delta/g, "\\Delta")
                                  .replace("Delta K_sector = monthly_rate * sector_weight * K", "\\Delta K_{sector} = \\text{monthly\\_rate} \\times \\text{sector\\_weight} \\times K");
                                return (
                                  <span className="inline-block bg-dark-300/80 px-2 py-1 rounded border border-dark-100/40 font-semibold mx-1 my-0.5 text-blue-300 overflow-x-auto max-w-full vertical-middle align-middle">
                                    <LaTeX math={cleanMath} block={false} />
                                  </span>
                                );
                              }
                              return <code className={className} {...props}>{children}</code>;
                            }
                          }}
                        >
                          {processedMarkdown}
                        </ReactMarkdown>

                        {/* Assumptions section */}
                        {evidence.assumptions && evidence.assumptions.length > 0 && (
                          <AssumptionsList assumptions={evidence.assumptions} />
                        )}
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
                          {(study.match_reasons?.length || study.relevance_tier) && (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {study.relevance_tier && (
                                <span className={`rounded-full border px-2 py-0.5 text-[8px] font-bold uppercase tracking-wider ${
                                  study.relevance_tier === "exact"
                                    ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-300"
                                    : "border-blue-500/30 bg-blue-950/20 text-blue-300"
                                }`}>
                                  {study.relevance_tier}
                                </span>
                              )}
                              {(study.match_reasons || []).slice(0, 4).map((reason) => (
                                <span
                                  key={reason}
                                  className="rounded-full border border-dark-100/50 bg-dark-300/60 px-2 py-0.5 text-[8px] font-bold uppercase tracking-wider text-gray-400"
                                >
                                  {reason}
                                </span>
                              ))}
                            </div>
                          )}
                          
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
                          No close historical precedent matched this scenario. The evidence report relies on simulation outputs.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Tab: Technical (Math & Data Proof) */}
                {activeTab === "technical" && (
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
                      <div className="bg-dark-300/80 rounded-xl border border-dark-100/40 p-4 overflow-x-auto max-w-full select-all scrollbar-thin">
                        <div className="min-w-max flex justify-center">
                          <LaTeX math="\Delta K_{sector} = \text{monthly\_rate} \times \text{sector\_weight} \times K" block={true} />
                        </div>
                      </div>
                      <p className="mt-3 text-[10px] text-gray-500 italic leading-[1.5]">
                        Note: Real estate index ($R$) and transit load ($T$) updates follow deterministic vector loops across neighboring cells.
                      </p>
                    </div>

                    {/* Case retrieval audit */}
                    {caseRetrieval && (
                      <div className="rounded-xl border border-dark-100/50 bg-dark-300/40 p-4">
                        <span className="text-[9px] font-bold uppercase tracking-widest text-emerald-400 block mb-1">Case Retrieval Audit</span>
                        <h4 className="text-xs font-bold text-gray-200 mb-2">Strict Precedent Matching</h4>
                        <div className="space-y-2 text-[11px]">
                          <div className="flex justify-between gap-3 border-b border-dark-100/20 py-1.5">
                            <span className="text-gray-500">City</span>
                            <span className="text-right text-gray-300 font-semibold">
                              {caseRetrieval.query_city?.replace("_", " ") || "Any"}
                            </span>
                          </div>
                          <div className="flex justify-between gap-3 border-b border-dark-100/20 py-1.5">
                            <span className="text-gray-500">Sectors</span>
                            <span className="text-right text-gray-300 font-semibold">
                              {caseRetrieval.query_sectors.map((sector) => SECTOR_LABELS[sector] || sector).join(", ") || "None"}
                            </span>
                          </div>
                          <div className="flex justify-between gap-3 border-b border-dark-100/20 py-1.5">
                            <span className="text-gray-500">Policies</span>
                            <span className="text-right text-gray-300 font-semibold">
                              {caseRetrieval.query_policies.join(", ") || "None"}
                            </span>
                          </div>
                          <div className="flex justify-between gap-3 border-b border-dark-100/20 py-1.5">
                            <span className="text-gray-500">Returned</span>
                            <span className="text-gray-300 font-mono font-semibold">{caseRetrieval.returned_count}</span>
                          </div>
                          <div className="flex justify-between gap-3 border-b border-dark-100/20 py-1.5">
                            <span className="text-gray-500">Weak omitted</span>
                            <span className="text-gray-300 font-mono font-semibold">{caseRetrieval.omitted_weak_count}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Data Audit trail */}
                    <div className="rounded-xl border border-dark-100/50 bg-dark-300/40 p-4">
                      <span className="text-[9px] font-bold uppercase tracking-widest text-amber-500 block mb-1">Data Source</span>
                      <h4 className="text-xs font-bold text-gray-200 mb-2">Baselines & Grid Density</h4>
                      <p className="text-[11px] leading-[1.5] text-gray-400 mb-3">
                        {currentFrame?.proof?.dataQuality || "Data quality details will appear after the simulation starts."}
                      </p>
                      <div className="space-y-2 text-[11px]">
                        <div className="flex justify-between border-b border-dark-100/20 py-1.5">
                          <span className="text-gray-500">Mode</span>
                          <span className="text-gray-300 font-semibold">
                            {currentFrame?.proof?.dataMode === "real_time" ? "Data-Informed" : "Estimated/Synthetic"}
                          </span>
                        </div>
                        {(["mobility", "jobs", "land_value", "census", "news"] as const).map((domain) => {
                          const source = dataSources[domain];
                          return (
                            <div key={domain} className="flex justify-between gap-3 border-b border-dark-100/20 py-1.5">
                              <span className="text-gray-500 capitalize">{domain.replace("_", " ")}</span>
                              <span className="text-right text-gray-300 font-semibold">
                                {source ? `${source.source} · ${source.freshness} · ${(source.confidence * 100).toFixed(0)}%` : "Missing"}
                              </span>
                            </div>
                          );
                        })}
                        <div className="flex justify-between border-b border-dark-100/20 py-1.5">
                          <span className="text-gray-500">Scenario expectation</span>
                          <span className="text-gray-300 font-semibold">
                            {prediction?.source === "deterministic_fallback" ? "Rule-based (no LLM)" : "LLM-assisted"}
                          </span>
                        </div>
                        <div className="flex justify-between border-b border-dark-100/20 py-1.5">
                          <span className="text-gray-500">Snapshot</span>
                          <span className="text-gray-300 font-mono font-semibold">{currentFrame?.proof?.snapshotId || "city baseline"}</span>
                        </div>
                        <div className="flex justify-between border-b border-dark-100/20 py-1.5">
                          <span className="text-gray-500">Active H3 Grid Cells</span>
                          <span className="text-gray-300 font-mono font-semibold">{evidence?.proof?.cellCount || currentFrame?.proof?.cellCount || 1415} cells</span>
                        </div>
                        {currentFrame?.proof?.overallConfidence != null && (
                          <div className="flex justify-between border-b border-dark-100/20 py-1.5">
                            <span className="text-gray-500">Simulation Confidence</span>
                            <span className={`font-semibold ${
                              currentFrame.proof.overallConfidence >= 0.7 ? "text-emerald-300" :
                              currentFrame.proof.overallConfidence >= 0.4 ? "text-amber-300" : "text-red-300"
                            }`}>
                              {(currentFrame.proof.overallConfidence * 100).toFixed(0)}% — {
                                currentFrame.proof.overallConfidence >= 0.7 ? "Based on measured data" :
                                currentFrame.proof.overallConfidence >= 0.4 ? "Based on estimated baselines" :
                                "Model-generated estimates"
                              }
                            </span>
                          </div>
                        )}
                        {currentFrame?.proof?.dataOrigins && Object.keys(currentFrame.proof.dataOrigins).length > 0 && (
                          <div className="pt-2">
                            <p className="text-[9px] font-bold uppercase tracking-widest text-violet-400 mb-1.5">Data Origins</p>
                            {Object.entries(currentFrame.proof.dataOrigins).map(([metric, origin]) => (
                              <div key={metric} className="flex justify-between gap-3 border-b border-dark-100/20 py-1">
                                <span className="text-gray-500 font-mono text-[10px]">{metric}</span>
                                <span className={`text-[10px] font-semibold ${
                                  origin === "real" ? "text-emerald-300" :
                                  origin === "estimated" ? "text-amber-300" : "text-gray-400"
                                }`}>
                                  {origin}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
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
