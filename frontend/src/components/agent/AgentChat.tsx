"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import {
  agentWsUrl,
  backoffDelay,
  chatReducer,
  getAgentStatus,
  initialChatState,
  parseServerEvent,
  shouldRetry,
  type ChatItem,
  type ConnectionStatus,
} from "@/lib/agentChat";

const TOKEN_KEY = "metropulse.agentToken";

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  unknown: "Not checked",
  checking: "Checking...",
  disabled: "Disabled",
  offline: "Backend offline",
  idle: "Ready",
  connecting: "Connecting...",
  retrying: "Busy, retrying...",
  open: "Connected",
  closed: "Ready",
};

const STATUS_DOT: Record<ConnectionStatus, string> = {
  unknown: "bg-slate-500",
  checking: "bg-amber-400",
  disabled: "bg-slate-500",
  offline: "bg-red-500",
  idle: "bg-sky-400",
  connecting: "bg-amber-400 animate-pulse",
  retrying: "bg-amber-400 animate-pulse",
  open: "bg-emerald-400",
  closed: "bg-sky-400",
};

function readToken(): string {
  try {
    return window.sessionStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

function saveToken(token: string) {
  try {
    if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
    else window.sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage blocked: token lives only in memory */
  }
}

function Item({ item, onOption, canReply }: { item: ChatItem; onOption: (o: string) => void; canReply: boolean }) {
  switch (item.kind) {
    case "user":
      return (
        <li className="ml-8 rounded-lg bg-sky-900/60 px-3 py-2 text-sm text-sky-50">{item.text}</li>
      );
    case "think":
      return (
        <li className="border-l-2 border-slate-600 pl-3 text-xs italic text-slate-400">
          {item.step != null && <span className="not-italic text-slate-500">Step {item.step} · </span>}
          {item.text}
        </li>
      );
    case "action":
      return (
        <li className="rounded border border-slate-700 bg-slate-900 px-3 py-1.5 font-mono text-xs text-amber-200">
          {item.tool}({Object.keys(item.args).length ? JSON.stringify(item.args) : ""})
        </li>
      );
    case "ask":
      return (
        <li className="mr-8 space-y-2 rounded-lg bg-slate-800 px-3 py-2 text-sm text-slate-100">
          <p>{item.question}</p>
          {item.options.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {item.options.map((o) => (
                <button
                  key={o}
                  type="button"
                  disabled={!canReply}
                  onClick={() => onOption(o)}
                  className="rounded border border-slate-600 px-2 py-0.5 text-xs hover:bg-slate-700 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                >
                  {o}
                </button>
              ))}
            </div>
          )}
        </li>
      );
    case "result":
      return (
        <li className="mr-8 whitespace-pre-wrap rounded-lg bg-slate-800 px-3 py-2 text-sm text-slate-100">
          {item.text}
        </li>
      );
    case "error":
      return (
        <li role="alert" className="rounded border border-red-800 bg-red-950/80 px-3 py-2 text-sm text-red-100">
          {item.text}
        </li>
      );
  }
}

/**
 * @param besidePanel true while the right-hand place panel (w-96) is open: on
 *   sm+ screens the widget moves left of it so it doesn't cover the panel.
 */
export function AgentChat({ besidePanel = false }: { besidePanel?: boolean } = {}) {
  const [open, setOpen] = useState(false);
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const [token, setToken] = useState("");
  const [draft, setDraft] = useState("");
  const socketRef = useRef<WebSocket | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [retryInMs, setRetryInMs] = useState<number | null>(null);
  const listRef = useRef<HTMLOListElement | null>(null);

  const checkStatus = useCallback(async () => {
    dispatch({ type: "status", status: "checking" });
    try {
      const s = await getAgentStatus();
      dispatch({ type: "status", status: s.enabled ? "idle" : "disabled" });
    } catch {
      dispatch({ type: "status", status: "offline" });
    }
  }, []);

  useEffect(() => {
    setToken(readToken());
  }, []);

  useEffect(() => {
    if (open && state.status === "unknown") void checkStatus();
  }, [open, state.status, checkStatus]);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [state.items.length]);

  // Closing our own socket: detach first so its onclose is ignored (a client
  // close reports code 1005, which would otherwise read as a failure).
  const cancelRetry = () => {
    const pending = retryTimerRef.current != null;
    if (retryTimerRef.current != null) clearTimeout(retryTimerRef.current);
    retryTimerRef.current = null;
    setRetryInMs(null);
    return pending;
  };

  const detach = () => {
    const hadRetry = cancelRetry();
    const ws = socketRef.current;
    socketRef.current = null;
    ws?.close();
    return hadRetry || ws != null;
  };

  // On unmount: cancel a pending retry and close the socket (refs only, no state updates).
  useEffect(
    () => () => {
      if (retryTimerRef.current != null) clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
      const ws = socketRef.current;
      socketRef.current = null;
      ws?.close();
    },
    []
  );

  const startSession = (message: string, retries = 0) => {
    detach();
    if (retries === 0) dispatch({ type: "user", text: message });
    dispatch({ type: "status", status: "connecting" });
    let sessionStarted = false;
    let ws: WebSocket;
    try {
      ws = new WebSocket(agentWsUrl(token));
    } catch {
      dispatch({ type: "error", text: "Invalid agent socket URL. Check NEXT_PUBLIC_WS_URL." });
      dispatch({ type: "status", status: "closed" });
      return;
    }
    socketRef.current = ws;
    ws.onopen = () => {
      dispatch({ type: "status", status: "open" });
      ws.send(JSON.stringify({ type: "AGENT_START", message }));
    };
    ws.onmessage = (e) => {
      const ev = parseServerEvent(e.data);
      if (!ev) return;
      sessionStarted = true;
      dispatch({ type: "server", event: ev });
    };
    ws.onclose = (e) => {
      if (socketRef.current !== ws) return; // superseded by a newer session
      socketRef.current = null;
      if (shouldRetry(e.code, retries, sessionStarted)) {
        const delay = backoffDelay(retries + 1);
        dispatch({ type: "status", status: "retrying" });
        setRetryInMs(delay);
        retryTimerRef.current = setTimeout(() => {
          retryTimerRef.current = null;
          setRetryInMs(null);
          startSession(message, retries + 1);
        }, delay);
        return;
      }
      dispatch({ type: "closed", clean: e.wasClean && e.code === 1000, code: e.code });
    };
  };

  const send = (text: string) => {
    const message = text.trim();
    if (!message) return;
    if (state.awaitingReply && socketRef.current?.readyState === WebSocket.OPEN) {
      dispatch({ type: "user", text: message });
      socketRef.current.send(JSON.stringify({ type: "AGENT_REPLY", message }));
    } else {
      if (message.length < 4) {
        dispatch({ type: "error", text: "Describe your goal in a few more words." });
        return;
      }
      startSession(message);
    }
    setDraft("");
  };

  const stop = () => {
    if (detach()) dispatch({ type: "closed", clean: true });
  };

  const disabled = state.status === "disabled";
  const offline = state.status === "offline";
  const busy =
    state.status === "connecting" || state.status === "retrying" || (state.running && !state.awaitingReply);
  const needsToken = !disabled && !offline && !token;
  const canSend = !disabled && !offline && !needsToken && !busy && state.status !== "checking";

  return (
    <div
      data-testid="agent-chat"
      className={`pointer-events-none absolute bottom-28 right-4 z-30 flex flex-col items-end gap-2 sm:bottom-6 ${
        besidePanel ? "sm:right-[25rem]" : ""
      }`}
    >
      {open && (
        <section
          aria-label="Planning agent"
          className={`pointer-events-auto flex ${disabled || offline ? "" : "h-[min(32rem,calc(100vh-10rem))]"} w-[min(24rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-lg border border-slate-700 bg-slate-950/95 shadow-xl`}
        >
          <header className="flex items-center gap-2 border-b border-slate-800 px-3 py-2">
            <h2 className="flex-1 text-sm font-semibold text-slate-100">Planning agent</h2>
            <span role="status" className="flex items-center gap-1.5 text-xs text-slate-400">
              <span aria-hidden className={`h-2 w-2 rounded-full ${STATUS_DOT[state.status]}`} />
              {STATUS_LABEL[state.status]}
            </span>
            {state.items.length > 0 && !state.running && (
              <button
                type="button"
                onClick={() => dispatch({ type: "reset" })}
                className="rounded px-1.5 text-xs text-slate-400 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              >
                Clear
              </button>
            )}
          </header>

          {disabled && (
            <div className="space-y-2 p-4 text-sm text-slate-300">
              <p>The agent is turned off on this server.</p>
              <p className="text-xs text-slate-500">
                An operator enables it by setting <code className="text-slate-400">AGENT_WS_TOKEN</code> on the
                backend.
              </p>
            </div>
          )}
          {offline && (
            <div className="space-y-3 p-4 text-sm text-slate-300">
              <p role="alert">Can&apos;t reach the backend to check the agent.</p>
              <button
                type="button"
                onClick={() => void checkStatus()}
                className="rounded border border-slate-600 px-3 py-1 text-slate-100 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              >
                Try again
              </button>
            </div>
          )}

          {!disabled && !offline && (
            <>
              {needsToken ? (
                <form
                  className="space-y-2 border-b border-slate-800 p-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const v = (new FormData(e.currentTarget).get("token") as string | null)?.trim() ?? "";
                    setToken(v);
                    saveToken(v);
                  }}
                >
                  <label htmlFor="agent-token" className="block text-xs text-slate-400">
                    Access token
                  </label>
                  <div className="flex gap-2">
                    <input
                      id="agent-token"
                      name="token"
                      type="password"
                      autoComplete="off"
                      className="min-w-0 flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                    />
                    <button
                      type="submit"
                      className="rounded bg-sky-700 px-3 py-1 text-sm text-white hover:bg-sky-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
                    >
                      Save
                    </button>
                  </div>
                </form>
              ) : (
                <div className="flex justify-end border-b border-slate-800 px-3 py-1">
                  <button
                    type="button"
                    onClick={() => {
                      setToken("");
                      saveToken("");
                    }}
                    className="text-xs text-slate-500 hover:text-slate-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                  >
                    Change token
                  </button>
                </div>
              )}

              <ol ref={listRef} aria-live="polite" className="flex-1 space-y-2 overflow-y-auto p-3">
                {state.items.length === 0 && (
                  <li className="text-sm text-slate-500">
                    Ask about a planning goal, e.g. &ldquo;Where should Bengaluru add bus depots?&rdquo;
                  </li>
                )}
                {state.items.map((item) => (
                  <Item key={item.id} item={item} canReply={state.awaitingReply} onOption={send} />
                ))}
                {busy && (
                  <li className="text-xs text-slate-500" aria-label="Agent is working">
                    {state.status === "retrying" && retryInMs != null
                      ? `The agent is busy. Retrying in ${Math.round(retryInMs / 1000)}s...`
                      : "Working..."}
                  </li>
                )}
              </ol>

              <form
                className="flex gap-2 border-t border-slate-800 p-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  send(draft);
                }}
              >
                <label htmlFor="agent-message" className="sr-only">
                  {state.awaitingReply ? "Reply to the agent" : "Message the agent"}
                </label>
                <input
                  id="agent-message"
                  value={draft}
                  maxLength={4000}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={!canSend}
                  placeholder={
                    needsToken ? "Enter the access token first" : state.awaitingReply ? "Your answer..." : "Ask the agent..."
                  }
                  className="min-w-0 flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100 placeholder:text-slate-500 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                />
                {busy ? (
                  <button
                    type="button"
                    onClick={stop}
                    className="rounded border border-slate-600 px-3 py-1 text-sm text-slate-200 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                  >
                    Stop
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={!canSend || !draft.trim()}
                    className="rounded bg-sky-700 px-3 py-1 text-sm text-white hover:bg-sky-600 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
                  >
                    Send
                  </button>
                )}
              </form>
            </>
          )}
        </section>
      )}
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="pointer-events-auto rounded-full border border-slate-700 bg-slate-950/90 px-4 py-2 text-sm text-slate-100 shadow-lg hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
      >
        {open ? "Close agent" : "Ask the agent"}
      </button>
    </div>
  );
}
