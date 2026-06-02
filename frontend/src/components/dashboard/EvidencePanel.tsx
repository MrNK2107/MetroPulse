"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSimulationStore, selectCurrentFrame } from "@/store/simulationStore";
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

type ActiveTab = "simple" | "detailed" | "cases" | "technical" | "history";

/** Simulation summary card — shown at top of Simple tab */
function SimulationSummaryCard() {
  const parsedScenario = useSimulationStore((s) => s.parsedScenario);
  const scenarioText = useSimulationStore((s) => s.scenarioText);
  const simulationDuration = useSimulationStore((s) => s.simulationDuration);
  const evidence = useSimulationStore((s) => s.evidence);
  const frames = useSimulationStore((s) => s.frames);
  const verdict = evidence?.translation?.overall_verdict ?? "";
  const city = parsedScenario?.city ?? "—";
  const horizon = parsedScenario?.horizon_months ?? frames.length;
  const verdictColor = verdict.includes("positive")
    ? "border-emerald-500/30 bg-emerald-950/15 text-emerald-300"
    : verdict.includes("negative")
    ? "border-red-500/30 bg-red-950/15 text-red-300"
    : "border-amber-500/30 bg-amber-950/15 text-amber-300";
  return (
    <div className={`rounded-xl border p-3.5 mb-3 ${verdictColor.split(" ").filter(c => c.startsWith("border") || c.startsWith("bg")).join(" ")}`}>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[11px]">
        <div className="flex items-center gap-1.5">
          <span className="text-base">🏙️</span>
          <div>
            <span className="text-[9px] font-bold uppercase tracking-wider text-gray-500 block">City</span>
            <span className="text-gray-200 font-semibold capitalize">{city.replace(/_/g, " ")}</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-base">📋</span>
          <div>
            <span className="text-[9px] font-bold uppercase tracking-wider text-gray-500 block">Duration</span>
            <span className="text-gray-200 font-semibold">{simulationDuration ? `${simulationDuration.toFixed(1)}s` : `${horizon} months`}</span>
          </div>
        </div>
        <div className="col-span-2 flex items-start gap-1.5">
          <span className="text-base shrink-0">🎯</span>
          <div className="min-w-0">
            <span className="text-[9px] font-bold uppercase tracking-wider text-gray-500 block">Scenario</span>
            <span className="text-gray-300 text-[11px] leading-[1.4] line-clamp-2">{scenarioText}</span>
          </div>
        </div>
        {verdict && (
          <div className="col-span-2 flex items-center gap-1.5 pt-1 border-t border-dark-100/30">
            <span className="text-base">⚖️</span>
            <div>
              <span className="text-[9px] font-bold uppercase tracking-wider text-gray-500 block">Verdict</span>
              <span className={`text-[11px] font-semibold italic ${verdict.includes("positive") ? "text-emerald-300" : verdict.includes("negative") ? "text-red-300" : "text-amber-300"}`}>
                {verdict}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function LaTeX({ math, block = false }: { math: string; block?: boolean }) {
  try {
    const html = getKatex()!.renderToString(math, {
      displayMode: block,
      throwOnError: false,
    });
    // Safe: html is produced by KaTeX renderToString, which escapes all user input and produces trusted markup
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

export const EvidencePanel = React.memo(function EvidencePanel() {
  const evidence = useSimulationStore((s) => s.evidence);
  const caseStudies = useSimulationStore((s) => s.caseStudies);
  const prediction = useSimulationStore((s) => s.prediction);
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);
  const currentFrame = useSimulationStore(selectCurrentFrame);
  const simulationHistory = useSimulationStore((s) => s.simulationHistory);
  const comparisonMode = useSimulationStore((s) => s.comparisonMode);
  const comparisonSimulation = useSimulationStore((s) => s.comparisonSimulation);

  const handleCompare = useCallback((entry: typeof simulationHistory[0]) => {
    useSimulationStore.setState({
      comparisonMode: true,
      comparisonSimulation: entry,
    });
  }, []);

  const handleClearComparison = useCallback(() => {
    useSimulationStore.setState({
      comparisonMode: false,
      comparisonSimulation: null,
    });
  }, []);

  const translation: TranslationResult = useMemo(() => ({
    headline: evidence?.translation?.headline ?? "",
    sector_impacts: evidence?.translation?.sector_impacts ?? [],
    takeaways: evidence?.translation?.takeaways ?? [],
    gdp_summary: evidence?.translation?.gdp_summary ?? "",
    unemployment_summary: evidence?.translation?.unemployment_summary ?? "",
    overall_verdict: evidence?.translation?.overall_verdict ?? "",
  }), [evidence?.translation]);
  const explainabilityTopDrivers = evidence?.explainability?.top_drivers ?? [];
  const hasSimpleView = Boolean(translation.sector_impacts.length);
  const [activeTab, setActiveTab] = useState<ActiveTab>("simple");
  const [caseSearch, setCaseSearch] = useState("");
  const [caseTierFilter, setCaseTierFilter] = useState<string>("all");
  const [showCopyToast, setShowCopyToast] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Filtered case studies
  const filteredCaseStudies = useMemo(() => {
    return caseStudies.filter((study) => {
      const matchesSearch = caseSearch === "" ||
        study.title.toLowerCase().includes(caseSearch.toLowerCase()) ||
        study.description.toLowerCase().includes(caseSearch.toLowerCase());
      const matchesTier = caseTierFilter === "all" || study.relevance_tier === caseTierFilter;
      return matchesSearch && matchesTier;
    });
  }, [caseStudies, caseSearch, caseTierFilter]);

  // Copy share link
  const handleShare = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShowCopyToast(true);
      setTimeout(() => setShowCopyToast(false), 2000);
    } catch { /* clipboard API may fail in some contexts */ }
  }, []);

  // Switch to simple tab when evidence with simpleView arrives after mount
  useEffect(() => {
    if (hasSimpleView && activeTab === "detailed") {
      setActiveTab("simple");
    }
  }, [hasSimpleView]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll to top of evidence panel when simulation completes
  useEffect(() => {
    if (pipelineStage === "done" && panelRef.current) {
      panelRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [pipelineStage]);

  const isDataAvailable = Boolean(evidence || currentFrame);
  const activeLoop = currentFrame?.activeLoop ?? (evidence?.proof?.activeEffects?.join(" -> ") || "complete");
  const dataSources = currentFrame?.proof?.dataSources ?? evidence?.proof?.dataSources ?? {};
  const caseRetrieval = evidence?.case_retrieval;

  // Streaming text reveal for Report tab — optimized with requestAnimationFrame
  // and throttled state updates (~100ms) to avoid re-rendering ReactMarkdown at 15ms
  const STREAM_WORDS_PER_TICK = 3;
  const THROTTLE_MS = 100;

  const [visibleWords, setVisibleWords] = useState(0);
  const totalWordsRef = useRef(0);
  const rafRef = useRef<number | null>(null);
  const wordsRef = useRef(0);
  const lastUpdateRef = useRef(0);

  useEffect(() => {
    if (!evidence?.markdown) {
      setVisibleWords(0);
      return;
    }
    const words = evidence.markdown.split(/\s+/);
    totalWordsRef.current = words.length;
    wordsRef.current = 0;
    lastUpdateRef.current = 0;
    setVisibleWords(0);

    const tick = (timestamp: number) => {
      if (wordsRef.current >= totalWordsRef.current) return;

      wordsRef.current += STREAM_WORDS_PER_TICK;

      // Throttle state updates to every ~100ms for smoother rendering
      if (timestamp - lastUpdateRef.current >= THROTTLE_MS || wordsRef.current >= totalWordsRef.current) {
        lastUpdateRef.current = timestamp;
        setVisibleWords(Math.min(wordsRef.current, totalWordsRef.current));
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
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
    <aside ref={panelRef} className="w-full md:w-[420px] flex flex-col md:border-l border-dark-100/50 bg-dark-200/95 backdrop-blur-md h-full shadow-2xl">
      {/* Panel Header */}
      <div className="border-b border-dark-100/40 p-5 bg-dark-300/40 select-none">
        <h2 className="text-sm font-bold uppercase tracking-widest text-gray-100">
          Evidence & Audit
        </h2>
        <p className="mt-1 text-[10px] text-gray-500 font-medium uppercase tracking-wider">
          What this means and why
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
          <div className="flex border-b border-dark-100/30 bg-dark-300/20 p-2 gap-1 select-none" role="tablist">
            {hasSimpleView && (
              <button
                onClick={() => setActiveTab("simple")}
                role="tab"
                id="tab-simple"
                aria-selected={activeTab === "simple"}
                aria-controls="tabpanel-simple"
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
              role="tab"
              id="tab-detailed"
              aria-selected={activeTab === "detailed"}
              aria-controls="tabpanel-detailed"
              className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all ${
                activeTab === "detailed"
                  ? "bg-blue-600/95 text-white shadow-md shadow-blue-500/10"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
              }`}
            >
              Report
            </button>
            <button
              onClick={() => setActiveTab("cases")}
              role="tab"
              id="tab-cases"
              aria-selected={activeTab === "cases"}
              aria-controls="tabpanel-cases"
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
              role="tab"
              id="tab-technical"
              aria-selected={activeTab === "technical"}
              aria-controls="tabpanel-technical"
              className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all ${
                activeTab === "technical"
                  ? "bg-blue-600/95 text-white shadow-md shadow-blue-500/10"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
              }`}
            >
              Technical
            </button>
            <button
              onClick={() => setActiveTab("history")}
              role="tab"
              id="tab-history"
              aria-selected={activeTab === "history"}
              aria-controls="tabpanel-history"
              className={`flex-1 text-[10px] font-bold uppercase tracking-wider py-1.5 rounded-lg transition-all ${
                activeTab === "history"
                  ? "bg-blue-600/95 text-white shadow-md shadow-blue-500/10"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-300/35"
              }`}
            >
              History
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
                  <div className="space-y-4" role="tabpanel" id="tabpanel-simple" aria-labelledby="tab-simple">
                    {/* Simulation summary card */}
                    <SimulationSummaryCard />

                    {/* Hero headline */}
                    <div className={`rounded-xl border p-4 ${
                      translation.overall_verdict.includes("positive")
                        ? "border-emerald-500/30 bg-emerald-950/15"
                        : translation.overall_verdict.includes("negative")
                        ? "border-red-500/30 bg-red-950/15"
                        : "border-amber-500/30 bg-amber-950/15"
                    }`}>
                      <p className="text-sm font-bold text-gray-100 leading-[1.5]">
                        {translation.headline}
                      </p>
                      <p className="mt-1 text-[10px] text-gray-400 italic">
                        {translation.overall_verdict}
                      </p>
                    </div>

                    {/* Sector impact cards */}
                    {translation.sector_impacts.slice(0, 3).map((impact) => (
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
                          <span
                            className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-dark-100/60 text-[7px] text-gray-400 cursor-help shrink-0"
                            title={`${impact.sector}: ${impact.direction === "positive" ? "Positive" : "Negative"} impact of ${impact.delta_pct.toFixed(0)}% on the ${impact.sector.replace(/_/g, " ")} sector.`}
                          >?</span>
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
                    {translation.takeaways.length > 0 && (
                      <div className="rounded-xl border border-blue-500/20 bg-blue-950/10 p-4">
                        <h4 className="text-[10px] font-bold uppercase tracking-wider text-blue-400 mb-2.5">
                          What this means for you
                        </h4>
                        <ol className="space-y-2">
                          {translation.takeaways.map((t, i) => (
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
                          {explainabilityTopDrivers.slice(0, 3).map((driver) => (
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
                        <p className="text-[9px] font-bold uppercase tracking-wider text-gray-500 mb-1 flex items-center justify-center gap-1">
                          Economy
                          <span
                            className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-dark-100/60 text-[7px] text-gray-400 cursor-help"
                            title="Change in city GDP from baseline. Positive = economic growth, negative = contraction. Example: If GDP grows 5%, a city like Bengaluru would see about ₹25,000 crores more economic activity."
                          >?</span>
                        </p>
                        <p className="text-xs font-bold text-gray-200">{translation.gdp_summary}</p>
                      </div>
                      <div className="rounded-xl border border-dark-100/50 bg-dark-300/30 p-3 text-center">
                        <p className="text-[9px] font-bold uppercase tracking-wider text-gray-500 mb-1 flex items-center justify-center gap-1">
                          Jobs
                          <span
                            className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-dark-100/60 text-[7px] text-gray-400 cursor-help"
                            title="Unemployment rate: Share of workforce actively seeking jobs. Below 6% is healthy; above 8% signals labor stress. Example: If unemployment rises from 5% to 8%, about 150,000 more people would be looking for jobs in Bengaluru."
                          >?</span>
                        </p>
                        <p className="text-xs font-bold text-gray-200">{translation.unemployment_summary}</p>
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
                        {evidence.explanation?.gdp_delta?.confidence != null && (() => {
                          const conf = evidence.explanation.gdp_delta.confidence;
                          return (
                          <p className="mt-2 text-[10px] text-gray-400">
                            Confidence: {(conf * 100).toFixed(0)}%
                            {conf < 0.5
                              ? " — model-generated estimate, interpret as directional"
                              : conf < 0.7
                              ? " — based on estimated baselines"
                              : " — based on measured data"}
                          </p>
                          );
                        })()}
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
                  <div className="space-y-4" role="tabpanel" id="tabpanel-detailed" aria-labelledby="tab-detailed">
                    {/* Share + PDF buttons */}
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => window.print()}
                        data-pdf-btn
                        className="flex items-center gap-1.5 rounded-lg border border-violet-500/30 bg-violet-950/20 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-violet-300 hover:text-violet-200 hover:border-violet-500/50 transition-all"
                      >
                        📄 Download PDF
                      </button>
                      <button
                        onClick={handleShare}
                        data-share-btn
                        className="flex items-center gap-1.5 rounded-lg border border-dark-100/50 bg-dark-300/40 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 hover:text-gray-200 hover:border-blue-500/30 transition-all"
                      >
                        🔗 Share
                      </button>
                    </div>
                    {showCopyToast && (
                      <div className="rounded-lg border border-emerald-500/30 bg-dark-200/95 px-3 py-2 text-xs text-emerald-300 shadow-md">
                        ✅ Link copied to clipboard!
                      </div>
                    )}
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
                  <div className="space-y-3" role="tabpanel" id="tabpanel-cases" aria-labelledby="tab-cases">
                    {/* Search & filter controls */}
                    {caseStudies.length > 0 && (
                      <div className="space-y-2">
                        <input
                          type="text"
                          placeholder="Search case studies..."
                          value={caseSearch}
                          onChange={(e) => setCaseSearch(e.target.value)}
                          className="w-full rounded-lg border border-dark-100/50 bg-dark-300/60 px-3 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500/50 transition-colors"
                        />
                        <div className="flex items-center gap-2">
                          <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Tier:</label>
                          <select
                            value={caseTierFilter}
                            onChange={(e) => setCaseTierFilter(e.target.value)}
                            className="rounded-lg border border-dark-100/50 bg-dark-300/60 px-2 py-1 text-[10px] text-gray-300 focus:outline-none focus:border-blue-500/50 transition-colors"
                          >
                            <option value="all">All</option>
                            <option value="exact">Exact</option>
                            <option value="related">Related</option>
                            <option value="weak">Contextual</option>
                          </select>
                          {caseSearch || caseTierFilter !== "all" ? (
                            <span className="text-[9px] text-gray-500">{filteredCaseStudies.length} of {caseStudies.length}</span>
                          ) : null}
                        </div>
                      </div>
                    )}
                    {filteredCaseStudies.length > 0 ? (
                      filteredCaseStudies.map((study) => (
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
                        <p className="text-xs text-gray-400 font-semibold">{caseStudies.length === 0 ? "No Case Studies Located" : "No matching case studies"}</p>
                        <p className="mt-1 text-[10px] text-gray-500 max-w-[240px] mx-auto leading-[1.5]">
                          {caseStudies.length === 0
                            ? "No close historical precedent matched this scenario. The evidence report relies on simulation outputs."
                            : "Try adjusting your search or filter criteria."}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Tab: Technical (Math & Data Proof) */}
                {activeTab === "technical" && (
                  <div className="space-y-4 leading-[1.5]" role="tabpanel" id="tabpanel-technical" aria-labelledby="tab-technical">
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

                {/* Tab: History (simulation history from localStorage) */}
                {activeTab === "history" && (
                  <div className="space-y-3" role="tabpanel" id="tabpanel-history" aria-labelledby="tab-history">
                    {comparisonMode && comparisonSimulation && (
                      <div className="rounded-xl border border-blue-500/30 bg-blue-950/20 p-3 flex items-center justify-between">
                        <div>
                          <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider">Comparing with: </span>
                          <span className="text-[11px] text-gray-300">{comparisonSimulation.city} — {comparisonSimulation.scenario.slice(0, 60)}…</span>
                        </div>
                        <button
                          onClick={handleClearComparison}
                          className="text-[9px] font-bold text-red-400 hover:text-red-300 border border-red-500/20 px-2 py-1 rounded-lg transition-colors"
                        >
                          ✕ Clear
                        </button>
                      </div>
                    )}
                    {simulationHistory.length > 0 ? (
                      simulationHistory.map((entry) => (
                        <div key={entry.id} className="rounded-xl border border-dark-100/50 bg-dark-300/30 p-4 hover:border-dark-100 transition-all">
                          <div className="flex justify-between items-start gap-3 border-b border-dark-100/30 pb-2">
                            <h4 className="text-xs font-bold text-gray-200">{entry.city}</h4>
                            <span className="text-[9px] text-gray-500 font-mono">
                              {new Date(entry.timestamp).toLocaleDateString()} {new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </span>
                          </div>
                          <p className="mt-2 text-[11px] text-gray-400 leading-[1.5] line-clamp-2">{entry.scenario}</p>
                          {entry.verdict && (
                            <p className="mt-2 text-[10px] text-emerald-400/80 italic">{entry.verdict}</p>
                          )}
                          <div className="mt-2 flex items-center justify-between">
                            <span className="text-[9px] text-gray-600 font-mono">ID: {entry.id}</span>
                            <button
                              onClick={() => handleCompare(entry)}
                              className={`text-[9px] font-bold px-2 py-1 rounded-lg border transition-colors ${
                                comparisonSimulation?.id === entry.id
                                  ? "text-blue-300 border-blue-500/40 bg-blue-950/30"
                                  : "text-gray-400 hover:text-blue-400 border-dark-100/30 hover:border-blue-500/20"
                              }`}
                            >
                              {comparisonSimulation?.id === entry.id ? "✓ Comparing" : "⇔ Compare"}
                            </button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-xl border border-dark-100/60 bg-dark-300/40 p-4 text-center py-8">
                        <span className="text-gray-600 text-2xl block mb-2">📋</span>
                        <p className="text-xs text-gray-400 font-semibold">No Simulation History</p>
                        <p className="mt-1 text-[10px] text-gray-500 max-w-[240px] mx-auto leading-[1.5]">
                          Completed simulations will appear here. Run a scenario to get started.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </aside>
  );
});
