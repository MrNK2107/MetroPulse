import type { SimulationParams, WSMessage } from "@/types/simulation";

export type FrameCallback = (frame: WSMessage & { type: "FRAME" }) => void;
export type InsightCallback = (insight: WSMessage & { type: "INSIGHT" }) => void;
export type ErrorCallback = (error: WSMessage & { type: "ERROR" }) => void;
export type DoneCallback = (done: WSMessage & { type: "DONE" }) => void;

export interface WSCallbacks {
  onFrame?: FrameCallback;
  onInsight?: InsightCallback;
  onError?: ErrorCallback;
  onDone?: DoneCallback;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private callbacks: WSCallbacks;
  private reconnectAttempts = 0;
  private maxRetries = 5;
  private shouldReconnect = false;

  constructor(url: string, callbacks: WSCallbacks) {
    this.url = url;
    this.callbacks = callbacks;
  }

  connect(params: SimulationParams): void {
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;

    try {
      this.ws = new WebSocket(this.url);
    } catch (err) {
      this.callbacks.onError?.({
        type: "ERROR",
        code: "CONNECTION_FAILED",
        message: "Failed to create WebSocket connection",
      });
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      const startMsg = { type: "START", params };
      this.ws?.send(JSON.stringify(startMsg));
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as WSMessage;
        this.handleMessage(data);
      } catch {
        console.warn("Failed to parse WS message");
      }
    };

    this.ws.onclose = () => {
      if (this.shouldReconnect) {
        this.attemptReconnect(params);
      }
    };

    this.ws.onerror = () => {
      if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
        this.attemptReconnect(params);
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
      case "FRAME":
        this.callbacks.onFrame?.(data);
        break;
      case "INSIGHT":
        this.callbacks.onInsight?.(data);
        break;
      case "ERROR":
        this.callbacks.onError?.(data);
        break;
      case "DONE":
        this.shouldReconnect = false;
        this.callbacks.onDone?.(data);
        break;
    }
  }

  private attemptReconnect(params: SimulationParams): void {
    if (this.reconnectAttempts >= this.maxRetries) {
      this.callbacks.onError?.({
        type: "ERROR",
        code: "RECONNECT_FAILED",
        message: "Failed to reconnect after 5 attempts",
      });
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * 2 ** (this.reconnectAttempts - 1), 30000);

    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect(params);
      }
    }, delay);
  }
}
