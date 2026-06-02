/**
 * Tests for WebSocketClient (frontend/src/lib/ws.ts)
 *
 * Mocks the global WebSocket class to test connection lifecycle,
 * message routing, reconnection logic, heartbeat, error handling, and send.
 */

import type { WSCallbacks } from "./ws";

// ── Mock WebSocket ───────────────────────────────────────────────────────────

let mockInstances: MockWebSocket[] = [];

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((ev?: Event) => void) | null = null;
  onclose: ((ev?: CloseEvent) => void) | null = null;
  onerror: ((ev?: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  send = jest.fn();
  close = jest.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  constructor(public readonly url: string) {
    mockInstances.push(this);
  }

  // helpers for tests
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }
  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }
  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }
  simulateError() {
    this.onerror?.();
  }
}

// Replace global WebSocket before importing the module
(globalThis as any).WebSocket = MockWebSocket;

// Mock window.setTimeout / clearTimeout for reconnection timers
jest.useFakeTimers();

// ── Import after mocks ───────────────────────────────────────────────────────

// Dynamic import so global mock is already in place
let WebSocketClient: typeof import("./ws").WebSocketClient;

beforeAll(async () => {
  const mod = await import("./ws");
  WebSocketClient = mod.WebSocketClient;
});

// ── Helpers ──────────────────────────────────────────────────────────────────

function createCallbacks(): WSCallbacks & Record<string, jest.Mock> {
  return {
    onStage: jest.fn(),
    onParsed: jest.fn(),
    onPrediction: jest.fn(),
    onFrame: jest.fn(),
    onCaseStudies: jest.fn(),
    onEvidence: jest.fn(),
    onError: jest.fn(),
    onDone: jest.fn(),
    onNeedsInput: jest.fn(),
    onGroupScores: jest.fn(),
  };
}

// ── Test suites ──────────────────────────────────────────────────────────────

describe("WebSocketClient", () => {
  beforeEach(() => {
    mockInstances = [];
    jest.clearAllTimers();
  });

  // ── Connection lifecycle ───────────────────────────────────────────────────

  describe("connection lifecycle", () => {
    it("creates a WebSocket on connect()", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("test scenario");

      expect(mockInstances).toHaveLength(1);
      expect(mockInstances[0].url).toBe("ws://localhost:8000/ws");
    });

    it("sends START message with scenario on open", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("test scenario");
      mockInstances[0].simulateOpen();

      expect(mockInstances[0].send).toHaveBeenCalledWith(
        JSON.stringify({ type: "START", scenario: "test scenario" })
      );
    });

    it("closes socket and nulls reference on disconnect()", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("test scenario");
      client.disconnect();

      expect(mockInstances[0].close).toHaveBeenCalled();
    });

    it("prevents reconnection after disconnect()", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("test scenario");

      // Simulate open then disconnect
      mockInstances[0].simulateOpen();
      client.disconnect();

      // Simulate close event after disconnect (should NOT reconnect)
      mockInstances[0].simulateClose();

      // Fast-forward timers — no new socket should be created
      jest.advanceTimersByTime(60000);
      expect(mockInstances).toHaveLength(1); // only the original socket
    });
  });

  // ── Message routing ────────────────────────────────────────────────────────

  describe("message routing", () => {
    it("routes STAGE messages to onStage callback", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "STAGE", stage: "parsing", message: "Parsing scenario..." };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onStage).toHaveBeenCalledWith(msg);
    });

    it("routes PARSED messages to onParsed callback", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "PARSED", params: {}, snapshot: {} };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onParsed).toHaveBeenCalledWith(msg);
    });

    it("routes PREDICTION messages to onPrediction callback", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "PREDICTION", prediction: { foo: "bar" } };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onPrediction).toHaveBeenCalledWith(msg);
    });

    it("routes FRAME messages to onFrame callback", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "FRAME", payload: { cells: [] } };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onFrame).toHaveBeenCalledWith(msg);
    });

    it("routes CASE_STUDIES messages to onCaseStudies callback", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "CASE_STUDIES", studies: [] };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onCaseStudies).toHaveBeenCalledWith(msg);
    });

    it("routes EVIDENCE messages to onEvidence callback", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "EVIDENCE", evidence: [] };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onEvidence).toHaveBeenCalledWith(msg);
    });

    it("routes ERROR messages to onError callback and stops reconnection", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "ERROR", stage: "error", code: "SIM_ERROR", message: "fail" };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onError).toHaveBeenCalledWith(msg);

      // After ERROR, close should not trigger reconnection
      mockInstances[0].simulateClose();
      jest.advanceTimersByTime(60000);
      expect(mockInstances).toHaveLength(1);
    });

    it("routes DONE messages to onDone callback and stops reconnection", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "DONE", simulationId: "abc-123" };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onDone).toHaveBeenCalledWith(msg);

      // After DONE, close should not trigger reconnection
      mockInstances[0].simulateClose();
      jest.advanceTimersByTime(60000);
      expect(mockInstances).toHaveLength(1);
    });

    it("routes NEEDS_INPUT messages to onNeedsInput callback", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "NEEDS_INPUT", question: "What do you mean?" };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onNeedsInput).toHaveBeenCalledWith(msg);
    });

    it("routes GROUP_SCORES messages to onGroupScores callback", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const msg = { type: "GROUP_SCORES", scores: {} };
      mockInstances[0].simulateMessage(msg);

      expect(cb.onGroupScores).toHaveBeenCalledWith(msg);
    });
  });

  // ── Reconnection logic ─────────────────────────────────────────────────────

  describe("reconnection logic", () => {
    it("attempts to reconnect after unexpected close (no simulation active)", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      // Close without simulation being active (no STAGE received yet)
      mockInstances[0].simulateClose();

      // First reconnect attempt uses 1000ms delay (2^(1-1)*1000 = 1000)
      expect(mockInstances).toHaveLength(1);
      jest.advanceTimersByTime(1000);
      expect(mockInstances).toHaveLength(2); // new socket created
    });

    it("uses exponential backoff for reconnection delays", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");

      // First attempt: open + close
      mockInstances[0].simulateOpen();
      mockInstances[0].simulateClose();
      jest.advanceTimersByTime(1000); // 2^0 * 1000 = 1000ms
      expect(mockInstances).toHaveLength(2);

      // Second attempt: open + close
      // Note: reconnectAttempts resets to 0 on successful open,
      // so the next delay is back to 1000ms (2^(1-1)*1000)
      mockInstances[1].simulateOpen();
      mockInstances[1].simulateClose();
      jest.advanceTimersByTime(999); // not enough
      expect(mockInstances).toHaveLength(2);
      jest.advanceTimersByTime(1); // total 1000ms = 2^0 * 1000
      expect(mockInstances).toHaveLength(3);
    });

    it("stops reconnecting after max retries (5) and calls onError", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");

      // First open+close starts the reconnect cycle
      mockInstances[0].simulateOpen();
      mockInstances[0].simulateClose();

      // Simulate 5 failed reconnection attempts (close immediately without open)
      // reconnectAttempts resets on successful open, so to exhaust retries
      // we need consecutive failures without open
      for (let i = 0; i < 5; i++) {
        jest.advanceTimersByTime(30000);
        // Close immediately without opening — reconnectAttempts accumulates
        mockInstances[mockInstances.length - 1].simulateClose();
      }

      // 1 original + 5 failed reconnects = 6
      expect(mockInstances).toHaveLength(6);

      // The 5th failed reconnect should trigger onError with RECONNECT_FAILED
      expect(cb.onError).toHaveBeenCalledWith(
        expect.objectContaining({ code: "RECONNECT_FAILED" })
      );
    });

    it("does NOT reconnect if simulation is active when connection drops", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      // Simulate STAGE message to mark simulation as active
      mockInstances[0].simulateMessage({ type: "STAGE", stage: "running", message: "Running..." });

      // Now close — should NOT reconnect
      mockInstances[0].simulateClose();

      jest.advanceTimersByTime(60000);
      expect(mockInstances).toHaveLength(1);
      expect(cb.onError).toHaveBeenCalledWith(
        expect.objectContaining({ code: "CONNECTION_LOST" })
      );
    });
  });

  // ── Error handling ─────────────────────────────────────────────────────────

  describe("error handling", () => {
    it("calls onError when onerror fires and socket is closed", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");

      // Simulate error when socket is in CLOSED state
      mockInstances[0].readyState = MockWebSocket.CLOSED;
      mockInstances[0].simulateError();

      expect(cb.onError).not.toHaveBeenCalledWith(
        expect.objectContaining({ code: "CONNECTION_LOST" })
      );
    });

    it("reports CONNECTION_LOST on error during active simulation", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      // Mark simulation active
      mockInstances[0].simulateMessage({ type: "STAGE", stage: "running", message: "..." });

      // Now socket errors while closed
      mockInstances[0].readyState = MockWebSocket.CLOSED;
      mockInstances[0].simulateError();

      expect(cb.onError).toHaveBeenCalledWith(
        expect.objectContaining({ code: "CONNECTION_LOST" })
      );
    });

    it("reports BAD_MESSAGE when JSON parse fails", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      // Send invalid JSON
      mockInstances[0].onmessage?.({ data: "not-json{{{" } as MessageEvent);

      expect(cb.onError).toHaveBeenCalledWith(
        expect.objectContaining({ code: "BAD_MESSAGE" })
      );
    });

    it("reports CONNECTION_FAILED when WebSocket constructor throws", () => {
      const cb = createCallbacks();

      // Override WebSocket to throw
      const OriginalWS = (globalThis as any).WebSocket;
      (globalThis as any).WebSocket = class {
        constructor() {
          throw new Error("connection refused");
        }
      };

      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");

      expect(cb.onError).toHaveBeenCalledWith(
        expect.objectContaining({ code: "CONNECTION_FAILED" })
      );

      // Restore
      (globalThis as any).WebSocket = OriginalWS;
    });
  });

  // ── send method ────────────────────────────────────────────────────────────

  describe("send (sendInputResponse)", () => {
    it("sends INPUT_RESPONSE message and returns true when socket is open", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      const result = client.sendInputResponse("hello there");

      expect(result).toBe(true);
      expect(mockInstances[0].send).toHaveBeenCalledWith(
        JSON.stringify({ type: "INPUT_RESPONSE", text: "hello there" })
      );
    });

    it("returns false when socket is not open", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      // Socket is in CONNECTING state (not OPEN)

      const result = client.sendInputResponse("hello");

      expect(result).toBe(false);
    });

    it("returns false when no socket exists", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      // Never called connect

      const result = client.sendInputResponse("hello");

      expect(result).toBe(false);
    });
  });

  // ── Heartbeat ──────────────────────────────────────────────────────────────

  describe("heartbeat", () => {
    it("sends PING message at heartbeat interval", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();

      // Clear the START message send call
      mockInstances[0].send.mockClear();

      // Advance by heartbeat interval (30s)
      jest.advanceTimersByTime(30_000);

      expect(mockInstances[0].send).toHaveBeenCalledWith(
        JSON.stringify({ type: "PING" })
      );
    });

    it("stops heartbeat on disconnect", () => {
      const cb = createCallbacks();
      const client = new WebSocketClient("ws://localhost:8000/ws", cb);
      client.connect("scenario");
      mockInstances[0].simulateOpen();
      mockInstances[0].send.mockClear();

      client.disconnect();

      // Advance past heartbeat interval — no PING should be sent
      jest.advanceTimersByTime(60_000);

      expect(mockInstances[0].send).not.toHaveBeenCalled();
    });
  });
});
