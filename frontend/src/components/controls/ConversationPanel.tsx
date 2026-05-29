"use client";

import { useRef, useEffect } from "react";
import { useSimulationStore, type ConversationMessage } from "@/store/simulationStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import { SECTOR_LABELS } from "@/types/simulation";
import { PresetSelector } from "./PresetSelector";

const QUICK_EXAMPLES = [
  "What if petrol prices spike in Mumbai?",
  "What happens when there's a tech boom in Bengaluru?",
  "Heavy rainfall devastates Chennai — what changes?",
  "What if interest rates rise sharply across India?",
];

export function ConversationPanel() {
  const scenarioText = useSimulationStore((s) => s.scenarioText);
  const setScenarioText = useSimulationStore((s) => s.setScenarioText);
  const parsed = useSimulationStore((s) => s.parsedScenario);
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);
  const error = useSimulationStore((s) => s.error);
  const messages = useSimulationStore((s) => s.conversationMessages);
  const pendingQuestion = useSimulationStore((s) => s.pendingQuestion);
  const conversationMode = useSimulationStore((s) => s.conversationMode);
  const setConversationMode = useSimulationStore((s) => s.setConversationMode);
  const resetAll = useSimulationStore((s) => s.resetAll);
  const { startSimulation, stopSimulation, sendResponse } = useWebSocket();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isRunning = !["idle", "done", "error", "needs_input"].includes(pipelineStage);
  const canRun = scenarioText.trim().length >= 4 && !isRunning;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleRun = () => {
    if (!canRun) return;
    const store = useSimulationStore.getState();
    store.addConversationMessage("user", scenarioText);
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/simulate";
    startSimulation(scenarioText, wsUrl);
  };

  const handleQuickReply = (option: string) => {
    sendResponse(option);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (pendingQuestion) {
        const input = (e.target as HTMLTextAreaElement).value.trim();
        if (input) {
          sendResponse(input);
          setScenarioText("");
        }
      } else if (canRun) {
        handleRun();
      }
    }
  };

  return (
    <aside className="w-[360px] bg-dark-200/95 border-r border-dark-100/50 h-full overflow-y-auto flex flex-col backdrop-blur-md shadow-2xl no-scrollbar">
      {/* Header */}
      <div className="p-5 border-b border-dark-100/40 bg-dark-300/40 select-none">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-blue-600 flex items-center justify-center font-bold text-xs shadow-md shadow-blue-500/20 text-white">
              M
            </div>
            <div>
              <h1 className="text-sm font-bold text-gray-100 uppercase tracking-widest font-sans">
                MetroPulse
              </h1>
              <p className="text-[10px] text-gray-500 uppercase font-medium tracking-wider">
                {conversationMode === "quick" ? "What If? Simulator" : "Direct Parameters"}
              </p>
            </div>
          </div>
          {/* Mode Toggle */}
          <div className="flex rounded-lg border border-dark-100/60 overflow-hidden text-[9px] font-bold">
            <button
              onClick={() => setConversationMode("quick")}
              className={`px-2.5 py-1 transition-all ${
                conversationMode === "quick"
                  ? "bg-blue-600 text-white"
                  : "bg-dark-300/50 text-gray-500 hover:text-gray-300"
              }`}
            >
              What If?
            </button>
            <button
              onClick={() => setConversationMode("deep")}
              className={`px-2.5 py-1 transition-all ${
                conversationMode === "deep"
                  ? "bg-blue-600 text-white"
                  : "bg-dark-300/50 text-gray-500 hover:text-gray-300"
              }`}
            >
              Direct Parameters
            </button>
          </div>
        </div>
      </div>

      {conversationMode === "quick" ? (
        <>
          {/* Presets */}
          <div className="px-5 pt-4">
            <PresetSelector />
          </div>

          {/* Conversation Messages */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
            {messages.length === 0 && (
              <div className="space-y-2">
                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                  Try a scenario
                </p>
                {QUICK_EXAMPLES.map((example) => (
                  <button
                    key={example}
                    onClick={() => setScenarioText(example)}
                    className="block w-full rounded-xl border border-dark-100/40 bg-dark-300/35 px-3 py-2.5 text-left text-xs text-gray-400 hover:border-blue-500/40 hover:text-gray-200 hover:bg-dark-300/60 transition-all duration-200"
                  >
                    {example}
                  </button>
                ))}
              </div>
            )}

            {messages.map((msg, i) => (
              <ChatBubble key={i} message={msg} />
            ))}

            {/* Quick Reply Buttons */}
            {pendingQuestion && pendingQuestion.options.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pl-8">
                {pendingQuestion.options.map((option) => (
                  <button
                    key={option}
                    onClick={() => handleQuickReply(option)}
                    className="rounded-lg border border-blue-500/30 bg-blue-950/40 px-3 py-1.5 text-[11px] font-medium text-blue-300 hover:bg-blue-900/50 hover:border-blue-400/50 transition-all"
                  >
                    {option}
                  </button>
                ))}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-dark-100/40 bg-dark-300/30">
            {pendingQuestion ? (
              <div className="space-y-2">
                <textarea
                  value={scenarioText}
                  onChange={(e) => setScenarioText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={2}
                  placeholder="Type your answer..."
                  className="w-full resize-none rounded-xl border border-dark-100/70 bg-dark-300/60 px-3.5 py-3 text-xs leading-relaxed text-gray-200 outline-none focus:border-blue-500/70 transition-all"
                />
                <button
                  onClick={() => {
                    sendResponse(scenarioText);
                    setScenarioText("");
                  }}
                  className="w-full rounded-xl bg-blue-600 py-2 text-xs font-bold text-white hover:bg-blue-500 transition-all"
                >
                  Send
                </button>
              </div>
            ) : (
              <>
                <textarea
                  value={scenarioText}
                  onChange={(e) => setScenarioText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={3}
                  placeholder="What if...?"
                  className="w-full resize-none rounded-xl border border-dark-100/70 bg-dark-300/60 px-3.5 py-3 text-xs leading-relaxed text-gray-200 outline-none focus:border-blue-500/70 transition-all"
                />
                <div className="flex gap-2 pt-2">
                  {isRunning ? (
                    <button
                      onClick={stopSimulation}
                      className="flex-1 rounded-xl bg-red-600 hover:bg-red-500 py-2.5 text-xs font-bold text-white transition-all active:scale-95"
                    >
                      Stop
                    </button>
                  ) : (
                    <button
                      disabled={!canRun}
                      onClick={handleRun}
                      className={`flex-1 rounded-xl py-2.5 text-xs font-bold transition-all active:scale-95 ${
                        canRun
                          ? "bg-blue-600 text-white hover:bg-blue-500"
                          : "bg-dark-300 text-gray-600 cursor-not-allowed"
                      }`}
                    >
                      Run Simulation
                    </button>
                  )}
                  <button
                    onClick={resetAll}
                    className="rounded-xl border border-dark-100/80 bg-dark-300/50 px-4 py-2.5 text-xs font-semibold text-gray-400 hover:text-gray-200 transition-all active:scale-95"
                  >
                    Reset
                  </button>
                </div>
              </>
            )}

            {error && (
              <div className="mt-2 rounded-xl border border-red-800 bg-red-950/30 px-3.5 py-3 text-xs text-red-300">
                {error}
              </div>
            )}
          </div>
        </>
      ) : (
        <>
          {/* Direct Parameters Interface */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5 no-scrollbar">
            {/* City Dropdown */}
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-gray-500 uppercase tracking-widest block">
                Target City
              </label>
              <select
                value={parsed?.city || "mumbai"}
                onChange={(e) => {
                  const cityId = e.target.value;
                  if (parsed) {
                    useSimulationStore.getState().setParsedScenario({
                      ...parsed,
                      city: cityId,
                      keywords: [cityId],
                    });
                    useSimulationStore.getState().flyToCity(cityId);
                  }
                }}
                className="w-full rounded-xl border border-dark-100/70 bg-dark-300/60 px-3 py-2.5 text-xs text-gray-200 outline-none focus:border-blue-500/70 transition-all cursor-pointer font-bold uppercase tracking-wider"
              >
                {Object.entries(useSimulationStore.getState().cityCoords).map(([id, config]) => (
                  <option key={id} value={id} className="bg-dark-200 text-gray-300">
                    {config.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Simulation Horizon Selector */}
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-gray-500 uppercase tracking-widest block">
                Simulation Horizon
              </label>
              <div className="flex gap-1.5">
                {[6, 12, 24, 60].map((months) => (
                  <button
                    key={months}
                    type="button"
                    onClick={() => useSimulationStore.getState().setHorizonMonths(months)}
                    className={`flex-1 rounded-xl py-2.5 text-xs font-bold transition-all border ${
                      parsed?.horizon_months === months
                        ? "bg-blue-600 border-blue-500/50 text-white shadow-lg shadow-blue-500/10"
                        : "bg-dark-300/40 border-dark-100/40 text-gray-500 hover:border-gray-600 hover:text-gray-300"
                    }`}
                  >
                    {months}m
                  </button>
                ))}
              </div>
            </div>

            {/* Active Policy Checkboxes */}
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-gray-500 uppercase tracking-widest block">
                Active Policy Interventions
              </label>
              <div className="grid grid-cols-2 gap-1.5 rounded-xl border border-dark-100/40 bg-dark-300/30 p-3.5">
                {[
                  "SEZ Notification",
                  "Smart City Mission",
                  "AMRUT",
                  "RERA Compliance",
                  "PM Awas Yojana",
                  "Make in India",
                  "Digital India",
                ].map((policy) => {
                  const active = parsed?.policies_active.includes(policy) ?? false;
                  return (
                    <button
                      key={policy}
                      type="button"
                      onClick={() => {
                        if (parsed) {
                          const policies = active
                            ? parsed.policies_active.filter((p) => p !== policy)
                            : [...parsed.policies_active, policy];
                          useSimulationStore.getState().setParsedScenario({
                            ...parsed,
                            policies_active: policies,
                          });
                        }
                      }}
                      className={`flex items-center gap-1.5 rounded-lg border px-2 py-1.5 text-left text-[9px] font-semibold transition-all ${
                        active
                          ? "bg-blue-950/40 border-blue-500/45 text-blue-300 shadow-md shadow-blue-500/5"
                          : "bg-dark-300/20 border-dark-100/45 text-gray-500 hover:text-gray-300 hover:border-gray-600"
                      }`}
                    >
                      <span className={`w-1 h-1 rounded-full shrink-0 ${active ? "bg-blue-400" : "bg-dark-100"}`} />
                      <span className="truncate">{policy}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* FDI Sector Sliders */}
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-gray-500 uppercase tracking-widest block">
                Sector Modifications
              </label>
              <div className="space-y-3.5 rounded-xl border border-dark-100/40 bg-dark-300/30 p-4">
                {Object.entries(SECTOR_LABELS).map(([key, label]) => {
                  const value = parsed?.sector_deltas[key] ?? 0;
                  const color =
                    value > 0
                      ? "text-emerald-400"
                      : value < 0
                        ? "text-red-400"
                        : "text-gray-500";

                  return (
                    <div key={key} className="space-y-1">
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-gray-400 font-medium">{label}</span>
                        <span className={`font-mono font-bold ${color}`}>
                          {value > 0 ? "+" : ""}
                          {value}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min={-50}
                        max={50}
                        step={5}
                        value={value}
                        onChange={(e) => useSimulationStore.getState().adjustSectorDelta(key, Number(e.target.value))}
                        className="w-full cursor-pointer accent-blue-500 h-1 bg-dark-100 rounded-lg appearance-none"
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Action Footer */}
          <div className="p-4 border-t border-dark-100/40 bg-dark-300/30">
            <div className="flex gap-2">
              {isRunning ? (
                <button
                  onClick={stopSimulation}
                  className="flex-1 rounded-xl bg-red-600 hover:bg-red-500 py-2.5 text-xs font-bold text-white transition-all active:scale-95"
                >
                  Stop
                </button>
              ) : (
                <button
                  disabled={!parsed}
                  onClick={() => {
                    if (parsed) {
                      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/simulate";
                      // Stringify the parsed state so the backend interceptor catches it as a JSON parameter shock
                      startSimulation(JSON.stringify(parsed), wsUrl);
                    }
                  }}
                  className="flex-1 rounded-xl bg-blue-600 hover:bg-blue-500 py-2.5 text-xs font-bold text-white transition-all active:scale-95 shadow-lg shadow-blue-500/15"
                >
                  Run Simulation
                </button>
              )}
              <button
                onClick={resetAll}
                className="rounded-xl border border-dark-100/80 bg-dark-300/50 px-4 py-2.5 text-xs font-semibold text-gray-400 hover:text-gray-200 transition-all active:scale-95"
              >
                Reset
              </button>
            </div>

            {error && (
              <div className="mt-2 rounded-xl border border-red-800 bg-red-950/30 px-3.5 py-3 text-xs text-red-300">
                {error}
              </div>
            )}
          </div>
        </>
      )}
    </aside>
  );
}

function ChatBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
          isUser
            ? "bg-blue-600/80 text-white rounded-br-md"
            : "bg-dark-300/70 text-gray-300 rounded-bl-md border border-dark-100/40"
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}
