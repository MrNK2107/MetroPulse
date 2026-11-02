/**
 * Socket-lifecycle tests for the /ws/agent chat client: connection URL, frame
 * streaming edge cases, busy (1013) retry with exponential backoff, and the
 * error states for refused / dropped sockets. Uses fake timers for the backoff.
 */
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AgentChat } from "./AgentChat";
import * as lib from "@/lib/agentChat";
import { MockSocket, installMockWebSocket } from "@/test-utils/mockWebSocket";

jest.mock("@/lib/agentChat", () => {
  const actual = jest.requireActual("@/lib/agentChat");
  return { ...actual, getAgentStatus: jest.fn() };
});
const mockedStatus = lib.getAgentStatus as jest.MockedFunction<typeof lib.getAgentStatus>;

installMockWebSocket();
beforeEach(() => {
  jest.useFakeTimers();
  window.sessionStorage.clear();
  window.sessionStorage.setItem("metropulse.agentToken", "s3cret&x");
  mockedStatus.mockReset();
  mockedStatus.mockResolvedValue({ enabled: true, available: true });
});
afterEach(() => {
  jest.useRealTimers();
});

const panel = () => screen.getByRole("region", { name: "Planning agent" });
const status = () => within(panel()).getByRole("status");

async function ask(message = "Plan bus depots") {
  const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
  const view = render(<AgentChat />);
  await user.click(screen.getByRole("button", { name: "Ask the agent" }));
  await within(panel()).findByText("Ready");
  await user.type(within(panel()).getByLabelText("Message the agent"), message);
  await user.click(within(panel()).getByRole("button", { name: "Send" }));
  return { user, view };
}

describe("AgentChat socket: connect", () => {
  it("opens one socket with the url-encoded token and sends AGENT_START on open", async () => {
    await ask();
    expect(MockSocket.instances).toHaveLength(1);
    expect(MockSocket.last.url).toMatch(/\/ws\/agent\?token=s3cret%26x$/);
    expect(MockSocket.last.sent).toEqual([]); // nothing is sent before the socket opens
    act(() => MockSocket.last.open());
    expect(MockSocket.last.sent).toEqual([{ type: "AGENT_START", message: "Plan bus depots" }]);
    expect(status()).toHaveTextContent("Connected");
  });

  it("disables the input while a session is running", async () => {
    await ask();
    act(() => {
      MockSocket.last.open();
      MockSocket.last.emit({ type: "AGENT_START" });
    });
    expect(within(panel()).getByLabelText("Message the agent")).toBeDisabled();
    expect(within(panel()).getByLabelText("Agent is working")).toHaveTextContent("Working...");
  });
});

describe("AgentChat socket: streaming", () => {
  it("renders frames in arrival order and ignores malformed or unknown frames", async () => {
    await ask();
    const ws = MockSocket.last;
    act(() => {
      ws.open();
      ws.emit({ type: "AGENT_START", agentId: "a1" });
      ws.emit({ type: "AGENT_THINK", content: "Step one", step: 1 });
      ws.emitRaw("{not json");
      ws.emit({ type: "SOMETHING_NEW", content: "should not render" });
      ws.emit({ type: "PONG" });
      ws.emit({ type: "AGENT_THINK", content: "Step two", step: 2 });
      ws.emit({ type: "AGENT_RESULT", content: "Final answer" });
    });
    const texts = within(panel())
      .getAllByRole("listitem")
      .map((li) => li.textContent ?? "");
    const idx = (t: string) => texts.findIndex((x) => x.includes(t));
    expect(idx("Plan bus depots")).toBeGreaterThanOrEqual(0);
    expect(idx("Plan bus depots")).toBeLessThan(idx("Step one"));
    expect(idx("Step one")).toBeLessThan(idx("Step two"));
    expect(idx("Step two")).toBeLessThan(idx("Final answer"));
    expect(within(panel()).queryByText(/should not render/)).toBeNull();
    expect(within(panel()).queryByRole("alert")).toBeNull();
  });

  it("a new question after AGENT_DONE opens a fresh socket", async () => {
    const { user } = await ask();
    const ws = MockSocket.last;
    act(() => {
      ws.open();
      ws.emit({ type: "AGENT_START" });
      ws.emit({ type: "AGENT_RESULT", content: "Done" });
      ws.emit({ type: "AGENT_DONE" });
      ws.serverClose(1000, true);
    });
    await user.type(within(panel()).getByLabelText("Message the agent"), "Another question");
    await user.click(within(panel()).getByRole("button", { name: "Send" }));
    expect(MockSocket.instances).toHaveLength(2);
    expect(ws.sent).toEqual([{ type: "AGENT_START", message: "Plan bus depots" }]);
    act(() => MockSocket.last.open());
    expect(MockSocket.last.sent).toEqual([{ type: "AGENT_START", message: "Another question" }]);
  });
});

describe("AgentChat socket: busy retry with backoff", () => {
  it("retries a 1013 refusal after 1s, 2s, 4s and then gives up with the busy message", async () => {
    await ask();
    act(() => MockSocket.last.serverClose(1013, true));
    expect(status()).toHaveTextContent("Busy, retrying");
    expect(within(panel()).getByLabelText("Agent is working")).toHaveTextContent("Retrying in 1s");

    act(() => jest.advanceTimersByTime(999));
    expect(MockSocket.instances).toHaveLength(1);
    act(() => jest.advanceTimersByTime(1));
    expect(MockSocket.instances).toHaveLength(2);
    expect(status()).toHaveTextContent("Connecting");

    act(() => MockSocket.last.serverClose(1013, true));
    expect(within(panel()).getByLabelText("Agent is working")).toHaveTextContent("Retrying in 2s");
    act(() => jest.advanceTimersByTime(2000));
    expect(MockSocket.instances).toHaveLength(3);

    act(() => MockSocket.last.serverClose(1013, true));
    act(() => jest.advanceTimersByTime(4000));
    expect(MockSocket.instances).toHaveLength(4);

    // 3 retries used up: the 4th refusal is final.
    act(() => MockSocket.last.serverClose(1013, true));
    act(() => jest.advanceTimersByTime(60_000));
    expect(MockSocket.instances).toHaveLength(4);
    expect(within(panel()).getByRole("alert")).toHaveTextContent(/busy/);
    expect(status()).toHaveTextContent("Ready");
    // The user's message is shown once, not once per attempt.
    expect(within(panel()).getAllByText("Plan bus depots")).toHaveLength(1);
  });

  it("a retry that connects carries on with the same message", async () => {
    await ask("Where should Pune add depots?");
    act(() => MockSocket.last.serverClose(1013, true));
    act(() => jest.advanceTimersByTime(1000));
    act(() => MockSocket.last.open());
    expect(MockSocket.last.sent).toEqual([{ type: "AGENT_START", message: "Where should Pune add depots?" }]);
    expect(status()).toHaveTextContent("Connected");
    expect(within(panel()).queryByRole("alert")).toBeNull();
  });

  it("Stop cancels a pending retry", async () => {
    const { user } = await ask();
    act(() => MockSocket.last.serverClose(1013, true));
    await user.click(within(panel()).getByRole("button", { name: "Stop" }));
    act(() => jest.advanceTimersByTime(60_000));
    expect(MockSocket.instances).toHaveLength(1);
    expect(status()).toHaveTextContent("Ready");
  });

  it("unmounting cancels a pending retry", async () => {
    const { view } = await ask();
    act(() => MockSocket.last.serverClose(1013, true));
    view.unmount();
    act(() => jest.advanceTimersByTime(60_000));
    expect(MockSocket.instances).toHaveLength(1);
  });

  it("does not retry a 1013 that arrives after the session started", async () => {
    await ask();
    act(() => {
      MockSocket.last.open();
      MockSocket.last.emit({ type: "AGENT_START" });
      MockSocket.last.serverClose(1013, true);
    });
    act(() => jest.advanceTimersByTime(60_000));
    expect(MockSocket.instances).toHaveLength(1);
    expect(within(panel()).getByRole("alert")).toHaveTextContent(/busy/);
  });
});

describe("AgentChat socket: error states", () => {
  it.each([
    [1008, /refused the connection/],
    [1006, /Could not reach the agent/],
  ])("close %i is not retried and explains itself", async (code, message) => {
    await ask();
    act(() => MockSocket.last.serverClose(code, false));
    act(() => jest.advanceTimersByTime(60_000));
    expect(MockSocket.instances).toHaveLength(1);
    expect(within(panel()).getByRole("alert")).toHaveTextContent(message);
  });

  it("a socket dropped mid-session stops the run and re-enables input", async () => {
    await ask();
    act(() => {
      MockSocket.last.open();
      MockSocket.last.emit({ type: "AGENT_START" });
      MockSocket.last.emit({ type: "AGENT_THINK", content: "Halfway" });
      MockSocket.last.serverClose(1006, false);
    });
    expect(within(panel()).getByText("Halfway")).toBeInTheDocument();
    expect(within(panel()).getByRole("alert")).toHaveTextContent(/Could not reach the agent/);
    expect(within(panel()).getByLabelText("Message the agent")).toBeEnabled();
    expect(within(panel()).getByRole("button", { name: "Send" })).toBeInTheDocument();
  });

  it("an invalid socket URL is reported instead of throwing", async () => {
    const Ctor = jest.fn(() => {
      throw new SyntaxError("bad url");
    });
    (global as unknown as { WebSocket: unknown }).WebSocket = Object.assign(Ctor, { OPEN: 1 });
    await ask();
    expect(within(panel()).getByRole("alert")).toHaveTextContent(/Invalid agent socket URL/);
    expect(status()).toHaveTextContent("Ready");
  });

  it("Clear after an error resets the transcript", async () => {
    const { user } = await ask();
    act(() => MockSocket.last.serverClose(1006, false));
    await user.click(within(panel()).getByRole("button", { name: "Clear" }));
    expect(within(panel()).queryByRole("alert")).toBeNull();
    expect(within(panel()).queryByText("Plan bus depots")).toBeNull();
  });
});
