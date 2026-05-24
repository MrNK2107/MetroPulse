import type {
  WSCaseStudiesMessage,
  WSDoneMessage,
  WSErrorMessage,
  WSEvidenceMessage,
  WSFrameMessage,
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
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private readonly maxRetries = 5;
  private shouldReconnect = false;

  constructor(private readonly url: string, private readonly callbacks: WSCallbacks) {}

  connect(scenario: string): void {
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;

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
      this.ws?.send(JSON.stringify({ type: "START", scenario }));
    };

    this.ws.onmessage = (event: MessageEvent) => {
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
      if (this.shouldReconnect) this.attemptReconnect(scenario);
    };

    this.ws.onerror = () => {
      if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
        this.attemptReconnect(scenario);
      }
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.ws?.close();
    this.ws = null;
  }

  private handleMessage(data: WSMessage): void {
    switch (data.type) {
      case "STAGE":
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
        this.callbacks.onError?.(data);
        break;
      case "DONE":
        this.shouldReconnect = false;
        this.callbacks.onDone?.(data);
        break;
    }
  }

  private attemptReconnect(scenario: string): void {
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
      if (this.shouldReconnect) this.connect(scenario);
    }, delay);
  }
}
