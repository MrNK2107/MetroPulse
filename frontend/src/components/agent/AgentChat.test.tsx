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
  window.sessionStorage.clear();
  mockedStatus.mockReset();
});

async function openPanel() {
  const user = userEvent.setup();
  render(<AgentChat />);
  await user.click(screen.getByRole("button", { name: "Ask the agent" }));
  return user;
}

const panel = () => screen.getByRole("region", { name: "Planning agent" });

describe("AgentChat", () => {
  it("does not check status until opened", () => {
    render(<AgentChat />);
    expect(mockedStatus).not.toHaveBeenCalled();
    expect(MockSocket.instances).toHaveLength(0);
  });

  it("shows the disabled state when the backend has no AGENT_WS_TOKEN", async () => {
    mockedStatus.mockResolvedValue({ enabled: false, available: false });
    await openPanel();
    expect(await within(panel()).findByText(/turned off on this server/)).toBeInTheDocument();
    expect(within(panel()).getByRole("status")).toHaveTextContent("Disabled");
    expect(within(panel()).queryByRole("textbox")).toBeNull();
    expect(MockSocket.instances).toHaveLength(0);
  });

  it("shows an offline state with retry when the status check fails", async () => {
    mockedStatus.mockRejectedValueOnce(new Error("down")).mockResolvedValueOnce({ enabled: true, available: true });
    const user = await openPanel();
    expect(await within(panel()).findByRole("alert")).toHaveTextContent(/reach the backend/);
    await user.click(within(panel()).getByRole("button", { name: "Try again" }));
    expect(await within(panel()).findByText("Ready")).toBeInTheDocument();
  });

  it("asks for a token, then streams a session and answers an AGENT_ASK", async () => {
    mockedStatus.mockResolvedValue({ enabled: true, available: true });
    const user = await openPanel();
    const tokenInput = await within(panel()).findByLabelText("Access token");
    expect(within(panel()).getByPlaceholderText("Enter the access token first")).toBeDisabled();
    await user.type(tokenInput, "secret");
    await user.click(within(panel()).getByRole("button", { name: "Save" }));
    expect(window.sessionStorage.getItem("metropulse.agentToken")).toBe("secret");

    await user.type(within(panel()).getByLabelText("Message the agent"), "Plan bus depots");
    await user.click(within(panel()).getByRole("button", { name: "Send" }));

    const ws = MockSocket.instances[0];
    expect(ws.url).toMatch(/\/ws\/agent\?token=secret$/);
    expect(within(panel()).getByRole("status")).toHaveTextContent("Connecting");
    act(() => ws.open());
    expect(ws.sent).toEqual([{ type: "AGENT_START", message: "Plan bus depots" }]);
    expect(within(panel()).getByRole("status")).toHaveTextContent("Connected");

    act(() => {
      ws.emit({ type: "AGENT_START", agentId: "a1" });
      ws.emit({ type: "AGENT_THINK", content: "Checking ridership", step: 1 });
      ws.emit({ type: "AGENT_ASK", question: "Which city?", options: ["Pune", "Delhi"] });
    });
    expect(within(panel()).getByText("Checking ridership")).toBeInTheDocument();
    await user.click(within(panel()).getByRole("button", { name: "Pune" }));
    expect(ws.sent[1]).toEqual({ type: "AGENT_REPLY", message: "Pune" });

    act(() => {
      ws.emit({ type: "AGENT_ACTION", tool: "query_city", args: { city: "pune" } });
      ws.emit({ type: "AGENT_RESULT", content: "Add 3 depots in Hadapsar." });
      ws.emit({ type: "AGENT_DONE", agentId: "a1" });
      ws.serverClose(1000, true);
    });
    expect(within(panel()).getByText(/query_city/)).toBeInTheDocument();
    expect(within(panel()).getByText("Add 3 depots in Hadapsar.")).toBeInTheDocument();
    expect(within(panel()).queryByRole("alert")).toBeNull();
    expect(within(panel()).getByRole("button", { name: "Send" })).toBeInTheDocument();
  });

  it("explains a refused socket and shows server errors", async () => {
    window.sessionStorage.setItem("metropulse.agentToken", "wrong");
    mockedStatus.mockResolvedValue({ enabled: true, available: true });
    const user = await openPanel();
    await within(panel()).findByText("Ready");
    await user.type(within(panel()).getByLabelText("Message the agent"), "Plan bus depots");
    await user.click(within(panel()).getByRole("button", { name: "Send" }));
    act(() => MockSocket.instances[0].serverClose(1006, false));
    expect(within(panel()).getByRole("alert")).toHaveTextContent(/Could not reach the agent/);

    await user.type(within(panel()).getByLabelText("Message the agent"), "Try again please");
    await user.click(within(panel()).getByRole("button", { name: "Send" }));
    const ws = MockSocket.instances[1];
    act(() => {
      ws.open();
      ws.emit({ type: "AGENT_ERROR", content: "The agent hit an internal error. Please try again." });
    });
    expect(within(panel()).getByText(/internal error/)).toBeInTheDocument();
  });

  it("rejects too-short messages locally without opening a socket", async () => {
    window.sessionStorage.setItem("metropulse.agentToken", "t");
    mockedStatus.mockResolvedValue({ enabled: true, available: true });
    const user = await openPanel();
    await within(panel()).findByText("Ready");
    await user.type(within(panel()).getByLabelText("Message the agent"), "hi");
    await user.click(within(panel()).getByRole("button", { name: "Send" }));
    expect(within(panel()).getByRole("alert")).toHaveTextContent(/few more words/);
    expect(MockSocket.instances).toHaveLength(0);
  });

  it("Stop closes the socket mid-session", async () => {
    window.sessionStorage.setItem("metropulse.agentToken", "t");
    mockedStatus.mockResolvedValue({ enabled: true, available: true });
    const user = await openPanel();
    await within(panel()).findByText("Ready");
    await user.type(within(panel()).getByLabelText("Message the agent"), "Plan bus depots");
    await user.click(within(panel()).getByRole("button", { name: "Send" }));
    const ws = MockSocket.instances[0];
    act(() => {
      ws.open();
      ws.emit({ type: "AGENT_START" });
    });
    await user.click(within(panel()).getByRole("button", { name: "Stop" }));
    expect(ws.readyState).toBe(MockSocket.CLOSED);
    expect(within(panel()).getByRole("button", { name: "Send" })).toBeInTheDocument();
  });
});
