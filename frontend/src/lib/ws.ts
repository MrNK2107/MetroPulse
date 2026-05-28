import type {
  WSCaseStudiesMessage,
  WSDoneMessage,
  WSErrorMessage,
  WSEvidenceMessage,
  WSFrameMessage,
  WSGroupScoresMessage,
  WSNeedsInputMessage,
  WSParsedMessage,
  WSPredictionMessage,
  WSStageMessage,
  WSMessage,
} from "@/types/simulation";

export interface WSCallbacks {
  onStage?: (stage: WSStageMessage) => void;
  onParsed?: (parsed: WSParsedMessage) => void;
  onPrediction?: (prediction: WSPredictionMessage) => void;
  onFrame?: (frame: WSFrameMessage) => void;
  onCaseStudies?: (studies: WSCaseStudiesMessage) => void;
  onEvidence?: (evidence: WSEvidenceMessage) => void;
  onError?: (error: WSErrorMessage) => void;
  onDone?: (done: WSDoneMessage) => void;
  onNeedsInput?: (msg: WSNeedsInputMessage) => void;
  onGroupScores?: (msg: WSGroupScoresMessage) => void;
}

const HEARTBEAT_INTERVAL_MS = 30_000;
const HEARTBEAT_TIMEOUT_MS = 10_000;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private readonly maxRetries = 5;
  private shouldReconnect = false;
  private simulationActive = false;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
  private scenario = "";

  constructor(private readonly url: string, private readonly callbacks: WSCallbacks) {}

  connect(scenario: string): void {
    this.scenario = scenario;
    this.shouldReconnect = true;
    this.simulationActive = false;
    this.reconnectAttempts = 0;

    this._createSocket();
  }

  private _createSocket(): void {
    try {
      this.ws = new WebSocket(this.url);
    } catch {
      this.callbacks.onError?.({
        type: "ERROR",
        stage: "error",
        code: "CONNECTION_FAILED",
        message: "Failed to create WebSocket connection.",
      });
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.ws?.send(JSON.stringify({ type: "START", scenario: this.scenario }));
      this._startHeartbeat();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      this._resetHeartbeatTimeout();
      try {
        this.handleMessage(JSON.parse(event.data) as WSMessage);
      } catch {
        this.callbacks.onError?.({
          type: "ERROR",
          stage: "error",
          code: "BAD_MESSAGE",
          message: "Backend sent a message the UI could not parse.",
        });
      }
    };

    this.ws.onclose = () => {
      this._stopHeartbeat();
      // Don't reconnect if simulation is mid-flight — report as error
      if (this.simulationActive) {
        this.shouldReconnect = false;
        this.callbacks.onError?.({
          type: "ERROR",
          stage: "error",
          code: "CONNECTION_LOST",
          message: "Connection lost during simulation. Please try again.",
        });
        return;
      }
      if (this.shouldReconnect) this._attemptReconnect();
    };

    this.ws.onerror = () => {
      if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
        this._stopHeartbeat();
        if (this.simulationActive) {
          this.shouldReconnect = false;
          this.callbacks.onError?.({
            type: "ERROR",
            stage: "error",
            code: "CONNECTION_LOST",
            message: "Connection lost during simulation. Please try again.",
          });
          return;
        }
        this._attemptReconnect();
      }
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.simulationActive = false;
    this._stopHeartbeat();
    this.ws?.close();
    this.ws = null;
  }

  sendInputResponse(text: string): boolean {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "INPUT_RESPONSE", text }));
      return true;
    }
    return false;
  }

  private handleMessage(data: WSMessage): void {
    switch (data.type) {
      case "STAGE":
        this.simulationActive = true;
        this.callbacks.onStage?.(data);
        break;
      case "PARSED":
        this.callbacks.onParsed?.(data);
        break;
      case "PREDICTION":
        this.callbacks.onPrediction?.(data);
        break;
      case "FRAME":
        this.callbacks.onFrame?.(data);
        break;
      case "CASE_STUDIES":
        this.callbacks.onCaseStudies?.(data);
        break;
      case "EVIDENCE":
        this.callbacks.onEvidence?.(data);
        break;
      case "ERROR":
        this.shouldReconnect = false;
        this.simulationActive = false;
        this._stopHeartbeat();
        this.callbacks.onError?.(data);
        break;
      case "DONE":
        this.shouldReconnect = false;
        this.simulationActive = false;
        this._stopHeartbeat();
        this.callbacks.onDone?.(data);
        break;
      case "NEEDS_INPUT":
        this.callbacks.onNeedsInput?.(data);
        break;
      case "GROUP_SCORES":
        this.callbacks.onGroupScores?.(data);
        break;
    }
  }

  private _startHeartbeat(): void {
    this._stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        // Send a ping frame (browser WS API doesn't expose ping, so send a JSON heartbeat)
        try {
          this.ws.send(JSON.stringify({ type: "PING" }));
        } catch {
          // Socket is dead
          this.ws?.close();
          return;
        }
        // Set timeout — if no pong/message within timeout, socket is stale
        this.heartbeatTimeout = setTimeout(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.close();
          }
        }, HEARTBEAT_TIMEOUT_MS);
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  private _stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  private _resetHeartbeatTimeout(): void {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  private _attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxRetries) {
      this.callbacks.onError?.({
        type: "ERROR",
        stage: "error",
        code: "RECONNECT_FAILED",
        message: "Failed to reconnect after 5 attempts.",
      });
      return;
    }

    this.reconnectAttempts += 1;
    const delay = Math.min(1000 * 2 ** (this.reconnectAttempts - 1), 30000);
    window.setTimeout(() => {
      if (this.shouldReconnect) this._createSocket();
    }, delay);
  }
}
