import {
  agentWsUrl,
  backoffDelay,
  MAX_BUSY_RETRIES,
  shouldRetry,
  chatReducer,
  closeMessage,
  initialChatState,
  parseServerEvent,
  type ChatAction,
  type ChatState,
} from "./agentChat";

const run = (actions: ChatAction[], from: ChatState = initialChatState) => actions.reduce(chatReducer, from);

describe("chatReducer", () => {
  it("streams a full session into ordered items", () => {
    const s = run([
      { type: "user", text: "Plan bus depots" },
      { type: "server", event: { type: "AGENT_START", agentId: "a1" } },
      { type: "server", event: { type: "AGENT_THINK", content: "Looking at data", step: 1 } },
      { type: "server", event: { type: "AGENT_ACTION", tool: "query_city", args: { city: "bengaluru" }, step: 1 } },
      { type: "server", event: { type: "AGENT_RESULT", content: "Add 3 depots" } },
      { type: "server", event: { type: "AGENT_DONE" } },
    ]);
    expect(s.items.map((i) => i.kind)).toEqual(["user", "think", "action", "result"]);
    expect(new Set(s.items.map((i) => i.id)).size).toBe(4);
    expect(s.running).toBe(false);
  });

  it("tracks AGENT_ASK until the user replies", () => {
    let s = run([
      { type: "server", event: { type: "AGENT_START" } },
      { type: "server", event: { type: "AGENT_ASK", question: "Which city?", options: ["Pune", "Delhi"] } },
    ]);
    expect(s.awaitingReply).toBe(true);
    expect(s.items[0]).toMatchObject({ kind: "ask", options: ["Pune", "Delhi"] });
    s = chatReducer(s, { type: "user", text: "Pune" });
    expect(s.awaitingReply).toBe(false);
  });

  it("tolerates a malformed ASK options field", () => {
    const s = chatReducer(initialChatState, {
      type: "server",
      event: { type: "AGENT_ASK", question: "?", options: "nope" as unknown as string[] },
    });
    expect(s.items[0]).toMatchObject({ kind: "ask", options: [] });
  });

  it("explains an unclean close but not the normal end of a session", () => {
    const clean = chatReducer({ ...initialChatState, running: true }, { type: "closed", clean: true, code: 1000 });
    expect(clean.items).toHaveLength(0);
    expect(clean.status).toBe("closed");
    const refused = chatReducer(initialChatState, { type: "closed", clean: false, code: 1006 });
    expect(refused.items[0]).toMatchObject({ kind: "error" });
    expect(refused.items[0]).toHaveProperty("text", closeMessage(1006));
  });

  it("shows server AGENT_ERROR text and falls back when empty", () => {
    const s = run([
      { type: "server", event: { type: "AGENT_ERROR", content: "Message too short." } },
      { type: "server", event: { type: "AGENT_ERROR" } },
    ]);
    expect(s.items.map((i) => (i.kind === "error" ? i.text : ""))).toEqual([
      "Message too short.",
      "The agent reported an error.",
    ]);
  });

  it("reset keeps a disabled status", () => {
    const s = run([{ type: "status", status: "disabled" }, { type: "error", text: "x" }, { type: "reset" }]);
    expect(s.items).toHaveLength(0);
    expect(s.status).toBe("disabled");
  });
});

describe("closeMessage", () => {
  it("distinguishes busy, refused and unreachable", () => {
    expect(closeMessage(1013)).toMatch(/busy/);
    expect(closeMessage(1008)).toMatch(/token/);
    expect(closeMessage(1006)).toMatch(/Could not reach/);
  });
});

describe("parseServerEvent", () => {
  it("accepts known events and rejects junk", () => {
    expect(parseServerEvent('{"type":"PONG"}')).toEqual({ type: "PONG" });
    expect(parseServerEvent('{"type":"WAT"}')).toBeNull();
    expect(parseServerEvent("not json")).toBeNull();
    expect(parseServerEvent("[1,2]")).toBeNull();
    expect(parseServerEvent(42)).toBeNull();
  });
});

describe("agentWsUrl", () => {
  const env = { ...process.env };
  afterEach(() => {
    process.env = { ...env };
  });

  it("uses NEXT_PUBLIC_WS_URL and encodes the token", () => {
    process.env.NEXT_PUBLIC_WS_URL = "wss://api.example.com/ws/agent";
    expect(agentWsUrl("a b&c")).toBe("wss://api.example.com/ws/agent?token=a%20b%26c");
  });

  it("rewrites the retired /ws/simulate endpoint", () => {
    process.env.NEXT_PUBLIC_WS_URL = "ws://localhost:8000/ws/simulate";
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
    expect(agentWsUrl("t")).toBe("ws://localhost:8000/ws/agent?token=t");
  });

  it("derives from the API URL when unset and appends the path to a bare base", () => {
    delete process.env.NEXT_PUBLIC_WS_URL;
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.com/";
    expect(agentWsUrl("t")).toBe("wss://api.example.com/ws/agent?token=t");
    process.env.NEXT_PUBLIC_WS_URL = "wss://api.example.com/ws";
    expect(agentWsUrl("t")).toBe("wss://api.example.com/ws/agent?token=t");
    process.env.NEXT_PUBLIC_WS_URL = "wss://api.example.com";
    expect(agentWsUrl("t")).toBe("wss://api.example.com/ws/agent?token=t");
  });
});

describe("backoffDelay / shouldRetry", () => {
  it("doubles from the base and caps at max", () => {
    expect([1, 2, 3, 4, 5].map((n) => backoffDelay(n))).toEqual([1000, 2000, 4000, 8000, 8000]);
    expect(backoffDelay(3, 250, 10_000)).toBe(1000);
    expect(backoffDelay(0)).toBe(1000);
    expect(backoffDelay(Number.NaN)).toBe(1000);
  });

  it("retries only a busy refusal before the session started, up to the limit", () => {
    expect(shouldRetry(1013, 0, false)).toBe(true);
    expect(shouldRetry(1013, MAX_BUSY_RETRIES - 1, false)).toBe(true);
    expect(shouldRetry(1013, MAX_BUSY_RETRIES, false)).toBe(false);
    expect(shouldRetry(1013, 0, true)).toBe(false);
    for (const code of [1000, 1006, 1008, 1011, undefined]) expect(shouldRetry(code, 0, false)).toBe(false);
  });
});
