/**
 * Client for the backend `/ws/agent` socket (see backend/app/ws/agent.py).
 *
 * Protocol, one session per socket:
 *   client -> AGENT_START {message}
 *   server -> AGENT_START {agentId}, then AGENT_THINK / AGENT_ACTION / AGENT_ASK ...
 *   client -> AGENT_REPLY {message}   (only after AGENT_ASK)
 *   server -> AGENT_RESULT, AGENT_DONE, then closes. AGENT_ERROR may arrive at any time.
 *
 * The socket is disabled server-side unless AGENT_WS_TOKEN is set. A browser
 * cannot see why a socket was refused (it only gets close code 1006), so the UI
 * asks GET /api/agent/status first to tell "disabled" from "bad token".
 */

export type ConnectionStatus =
  | "unknown" // status not checked yet
  | "checking"
  | "disabled" // backend has no AGENT_WS_TOKEN
  | "offline" // backend unreachable
  | "idle" // enabled, no socket open
  | "connecting"
  | "retrying" // server said busy (1013); waiting before the next attempt
  | "open"
  | "closed";

export type ChatItem =
  | { id: number; kind: "user"; text: string }
  | { id: number; kind: "think"; text: string; step?: number }
  | { id: number; kind: "action"; tool: string; args: Record<string, unknown>; step?: number }
  | { id: number; kind: "ask"; question: string; options: string[] }
  | { id: number; kind: "result"; text: string }
  | { id: number; kind: "error"; text: string };

export interface ChatState {
  status: ConnectionStatus;
  items: ChatItem[];
  /** True while an AGENT_ASK is waiting for an AGENT_REPLY. */
  awaitingReply: boolean;
  /** True from AGENT_START until AGENT_DONE / close. */
  running: boolean;
  nextId: number;
}

export type ServerEvent =
  | { type: "AGENT_START"; agentId?: string }
  | { type: "AGENT_THINK"; content?: string; step?: number }
  | { type: "AGENT_ACTION"; tool?: string; args?: Record<string, unknown>; step?: number }
  | { type: "AGENT_ASK"; question?: string; options?: string[]; step?: number }
  | { type: "AGENT_RESULT"; content?: string; step?: number }
  | { type: "AGENT_DONE"; agentId?: string }
  | { type: "AGENT_ERROR"; content?: string }
  | { type: "PONG" };

export type ChatAction =
  | { type: "status"; status: ConnectionStatus }
  | { type: "user"; text: string }
  | { type: "server"; event: ServerEvent }
  | { type: "closed"; clean: boolean; code?: number }
  | { type: "error"; text: string }
  | { type: "reset" };

export const initialChatState: ChatState = {
  status: "unknown",
  items: [],
  awaitingReply: false,
  running: false,
  nextId: 1,
};

type NewItem = ChatItem extends infer T ? (T extends ChatItem ? Omit<T, "id"> : never) : never;

function push(state: ChatState, item: NewItem): ChatState {
  return {
    ...state,
    items: [...state.items, { ...item, id: state.nextId } as ChatItem],
    nextId: state.nextId + 1,
  };
}

export function closeMessage(code?: number): string {
  if (code === 1013) return "The agent is busy (too many sessions). Try again in a minute.";
  if (code === 1008) return "The agent refused the connection. Check the access token.";
  return "Could not reach the agent. Check the access token and that the backend is running.";
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "status":
      return { ...state, status: action.status };
    case "user":
      return push({ ...state, awaitingReply: false }, { kind: "user", text: action.text });
    case "error":
      return push(state, { kind: "error", text: action.text });
    case "reset":
      return { ...initialChatState, status: state.status === "disabled" ? "disabled" : "idle" };
    case "closed": {
      const next: ChatState = { ...state, status: "closed", running: false, awaitingReply: false };
      // The server always closes cleanly (1000) after AGENT_DONE or after sending
      // its own AGENT_ERROR. A refused or dropped socket (1006/1008/1013) needs
      // an explanation of its own.
      return action.clean ? next : push(next, { kind: "error", text: closeMessage(action.code) });
    }
    case "server": {
      const ev = action.event;
      switch (ev.type) {
        case "AGENT_START":
          return { ...state, running: true };
        case "AGENT_THINK":
          return push(state, { kind: "think", text: ev.content ?? "", step: ev.step });
        case "AGENT_ACTION":
          return push(state, { kind: "action", tool: ev.tool ?? "tool", args: ev.args ?? {}, step: ev.step });
        case "AGENT_ASK":
          return push(
            { ...state, awaitingReply: true },
            { kind: "ask", question: ev.question ?? "", options: Array.isArray(ev.options) ? ev.options : [] }
          );
        case "AGENT_RESULT":
          return push(state, { kind: "result", text: ev.content ?? "" });
        case "AGENT_DONE":
          return { ...state, running: false, awaitingReply: false };
        case "AGENT_ERROR":
          return push(state, { kind: "error", text: ev.content || "The agent reported an error." });
        default:
          return state;
      }
    }
    default:
      return state;
  }
}

/** How many times a "busy" (1013) refusal is retried before giving up. */
export const MAX_BUSY_RETRIES = 3;

/**
 * Exponential backoff for retry `attempt` (1-based): base, 2*base, 4*base ...
 * capped at `max`. Deterministic so the UI can show the countdown.
 */
export function backoffDelay(attempt: number, base = 1000, max = 8000): number {
  if (!Number.isFinite(attempt) || attempt < 1) return base;
  return Math.min(max, base * 2 ** (attempt - 1));
}

/**
 * Only a "busy" refusal (1013) that arrives before the server started a session
 * is retried automatically. A refused token (1008/1006) will not get better by
 * retrying, and a session that already started cannot be resumed on a new socket.
 */
export function shouldRetry(code: number | undefined, retriesSoFar: number, sessionStarted: boolean): boolean {
  return code === 1013 && !sessionStarted && retriesSoFar < MAX_BUSY_RETRIES;
}

const KNOWN = new Set([
  "AGENT_START",
  "AGENT_THINK",
  "AGENT_ACTION",
  "AGENT_ASK",
  "AGENT_RESULT",
  "AGENT_DONE",
  "AGENT_ERROR",
  "PONG",
]);

/** Parses one socket frame; returns null for anything that is not a known event. */
export function parseServerEvent(raw: unknown): ServerEvent | null {
  if (typeof raw !== "string") return null;
  try {
    const data = JSON.parse(raw);
    if (data && typeof data === "object" && KNOWN.has(data.type)) return data as ServerEvent;
  } catch {
    /* ignore malformed frames */
  }
  return null;
}

const apiBase = () => process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** ws(s)://host/ws/agent, from NEXT_PUBLIC_WS_URL or derived from the API URL. */
export function agentWsUrl(token: string): string {
  let url = process.env.NEXT_PUBLIC_WS_URL || "";
  if (!url || /\/ws\/simulate\/?$/.test(url)) {
    // Retired endpoint or unset: derive from the API base.
    url = apiBase().replace(/^http/, "ws").replace(/\/+$/, "") + "/ws/agent";
  } else if (!/\/ws\/agent\/?$/.test(url)) {
    url = url.replace(/\/+$/, "") + (/\/ws$/.test(url.replace(/\/+$/, "")) ? "/agent" : "/ws/agent");
  }
  return `${url}?token=${encodeURIComponent(token)}`;
}

export interface AgentStatus {
  enabled: boolean;
  available: boolean;
}

export async function getAgentStatus(): Promise<AgentStatus> {
  const res = await fetch(`${apiBase()}/api/agent/status`);
  if (!res.ok) throw new Error(`Status check failed (${res.status})`);
  const body = await res.json();
  return { enabled: !!body?.data?.enabled, available: !!body?.data?.available };
}
