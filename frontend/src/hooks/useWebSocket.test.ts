/**
 * Tests for useWebSocket hook (frontend/src/hooks/useWebSocket.ts)
 *
 * Mocks the WebSocketClient class and the simulation store,
 * then tests startSimulation, stopSimulation, and sendResponse.
 */

// ── Mocks ────────────────────────────────────────────────────────────────────

const mockConnect = jest.fn();
const mockDisconnect = jest.fn();
const mockSendInputResponse = jest.fn();

jest.mock("@/lib/ws", () => ({
  WebSocketClient: jest.fn().mockImplementation((_url: string, _callbacks: any) => ({
    connect: mockConnect,
    disconnect: mockDisconnect,
    sendInputResponse: mockSendInputResponse,
  })),
}));

// Capture the callbacks passed to WebSocketClient so we can invoke them in tests
let capturedCallbacks: Record<string, Function> = {};
const { WebSocketClient } = require("@/lib/ws");

// Wrap the constructor to capture callbacks
(WebSocketClient as jest.Mock).mockImplementation((url: string, callbacks: any) => {
  capturedCallbacks = callbacks;
  return {
    connect: mockConnect,
    disconnect: mockDisconnect,
    sendInputResponse: mockSendInputResponse,
  };
});

// Mock the simulation store
const mockStore = {
  setError: jest.fn(),
  resetRun: jest.fn(),
  setStage: jest.fn(),
  setParsedScenario: jest.fn(),
  setRegionBoundary: jest.fn(),
  setPrediction: jest.fn(),
  addFrame: jest.fn(),
  setCaseStudies: jest.fn(),
  setEvidence: jest.fn(),
  setSimulationId: jest.fn(),
  setPendingQuestion: jest.fn(),
  addConversationMessage: jest.fn(),
  setGroupScores: jest.fn(),
};

jest.mock("@/store/simulationStore", () => ({
  useSimulationStore: {
    getState: jest.fn(() => mockStore),
  },
}));

// ── Import after mocks ───────────────────────────────────────────────────────

import { renderHook, act } from "@testing-library/react";
import { useWebSocket } from "./useWebSocket";

// ── Test suites ──────────────────────────────────────────────────────────────

describe("useWebSocket", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSendInputResponse.mockReturnValue(true);
    capturedCallbacks = {};
  });

  // ── startSimulation ────────────────────────────────────────────────────────

  describe("startSimulation", () => {
    it("rejects scenarios shorter than 10 characters", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("short", "ws://localhost:8000/ws");
      });

      expect(mockStore.setError).toHaveBeenCalledWith(
        expect.stringContaining("at least 10 characters")
      );
      expect(mockConnect).not.toHaveBeenCalled();
    });

    it("creates a WebSocketClient and connects with the scenario", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation(
          "What happens to Hyderabad if pharma FDI drops 40%?",
          "ws://localhost:8000/ws"
        );
      });

      expect(WebSocketClient).toHaveBeenCalledWith("ws://localhost:8000/ws", expect.any(Object));
      expect(mockConnect).toHaveBeenCalledWith(
        "What happens to Hyderabad if pharma FDI drops 40%?"
      );
    });

    it("resets run before starting a new simulation", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("a valid scenario that is long enough", "ws://localhost:8000/ws");
      });

      expect(mockStore.resetRun).toHaveBeenCalled();
    });

    it("disconnects existing client before starting a new one", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("first scenario that is long enough", "ws://localhost:8000/ws");
      });

      act(() => {
        result.current.startSimulation("second scenario that is also long enough", "ws://localhost:8000/ws");
      });

      // disconnect should be called once (for the first client)
      expect(mockDisconnect).toHaveBeenCalledTimes(1);
      // connect should be called twice
      expect(mockConnect).toHaveBeenCalledTimes(2);
    });
  });

  // ── Callbacks update store ─────────────────────────────────────────────────

  describe("message handlers update store", () => {
    it("onStage calls setStage on the store", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        capturedCallbacks.onStage({ stage: "parsing", message: "Parsing..." });
      });

      expect(mockStore.setStage).toHaveBeenCalledWith("parsing", "Parsing...");
    });

    it("onParsed calls setParsedScenario and optionally setRegionBoundary", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      // Without boundary
      act(() => {
        capturedCallbacks.onParsed({ params: { a: 1 }, snapshot: { b: 2 } });
      });
      expect(mockStore.setParsedScenario).toHaveBeenCalledWith({ a: 1 }, { b: 2 });
      expect(mockStore.setRegionBoundary).not.toHaveBeenCalled();

      // With boundary
      act(() => {
        capturedCallbacks.onParsed({ params: { a: 1 }, snapshot: { b: 2 }, boundary: { type: "Feature" } });
      });
      expect(mockStore.setRegionBoundary).toHaveBeenCalledWith({ type: "Feature" });
    });

    it("onPrediction calls setPrediction", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        capturedCallbacks.onPrediction({ prediction: { impact: -0.3 } });
      });

      expect(mockStore.setPrediction).toHaveBeenCalledWith({ impact: -0.3 });
    });

    it("onFrame calls addFrame", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        capturedCallbacks.onFrame({ payload: { cells: [1, 2, 3] } });
      });

      expect(mockStore.addFrame).toHaveBeenCalledWith({ cells: [1, 2, 3] });
    });

    it("onCaseStudies calls setCaseStudies", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        capturedCallbacks.onCaseStudies({ studies: [{ id: 1 }] });
      });

      expect(mockStore.setCaseStudies).toHaveBeenCalledWith([{ id: 1 }]);
    });

    it("onEvidence calls setEvidence", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        capturedCallbacks.onEvidence({ evidence: [{ url: "http://example.com" }] });
      });

      expect(mockStore.setEvidence).toHaveBeenCalledWith([{ url: "http://example.com" }]);
    });

    it("onError calls setError", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        capturedCallbacks.onError({ message: "Something broke", stage: "simulation" });
      });

      expect(mockStore.setError).toHaveBeenCalledWith("Something broke", "simulation");
    });

    it("onDone calls setSimulationId", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        capturedCallbacks.onDone({ simulationId: "sim-abc-123" });
      });

      expect(mockStore.setSimulationId).toHaveBeenCalledWith("sim-abc-123");
    });

    it("onNeedsInput calls setPendingQuestion and addConversationMessage", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        capturedCallbacks.onNeedsInput({ question: "Can you clarify?" });
      });

      expect(mockStore.setPendingQuestion).toHaveBeenCalledWith({ question: "Can you clarify?" });
      expect(mockStore.addConversationMessage).toHaveBeenCalledWith("system", "Can you clarify?");
    });

    it("onGroupScores calls setGroupScores", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        capturedCallbacks.onGroupScores({ scores: { groupA: 0.8 } });
      });

      expect(mockStore.setGroupScores).toHaveBeenCalledWith({ scores: { groupA: 0.8 } });
    });
  });

  // ── stopSimulation ─────────────────────────────────────────────────────────

  describe("stopSimulation", () => {
    it("disconnects the client and sets an error message", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        result.current.stopSimulation();
      });

      expect(mockDisconnect).toHaveBeenCalled();
      expect(mockStore.setError).toHaveBeenCalledWith("Simulation stopped by user.");
    });

    it("is safe to call when no simulation is running", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.stopSimulation();
      });

      expect(mockDisconnect).not.toHaveBeenCalled();
    });
  });

  // ── sendResponse ───────────────────────────────────────────────────────────

  describe("sendResponse", () => {
    it("sends message through the client and updates store", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        result.current.sendResponse("my answer");
      });

      expect(mockStore.addConversationMessage).toHaveBeenCalledWith("user", "my answer");
      expect(mockStore.setPendingQuestion).toHaveBeenCalledWith(null);
      expect(mockSendInputResponse).toHaveBeenCalledWith("my answer");
    });

    it("sets error when send fails (client returns false)", () => {
      mockSendInputResponse.mockReturnValue(false);
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.startSimulation("valid scenario for testing purposes", "ws://localhost:8000/ws");
      });

      act(() => {
        result.current.sendResponse("my answer");
      });

      expect(mockStore.setError).toHaveBeenCalledWith(
        expect.stringContaining("Could not send your response")
      );
    });

    it("sets error when no client exists", () => {
      const { result } = renderHook(() => useWebSocket());

      act(() => {
        result.current.sendResponse("my answer");
      });

      expect(mockStore.addConversationMessage).toHaveBeenCalledWith("user", "my answer");
      expect(mockStore.setPendingQuestion).toHaveBeenCalledWith(null);
      // sendInputResponse was not called since clientRef.current is null
      // The ?? false handles undefined → false → setError
      expect(mockStore.setError).toHaveBeenCalledWith(
        expect.stringContaining("Could not send your response")
      );
    });
  });
});
