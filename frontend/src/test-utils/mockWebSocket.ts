/**
 * In-memory WebSocket stand-in for jsdom tests. Tests drive the "server" side
 * with open(), emit(), emitRaw() and serverClose(); everything the client sends
 * is parsed into `sent`.
 */
export class MockSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: MockSocket[] = [];
  readyState = MockSocket.CONNECTING;
  sent: unknown[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number; wasClean: boolean }) => void) | null = null;
  constructor(public url: string) {
    MockSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(JSON.parse(data));
  }
  close() {
    this.serverClose(1000, true);
  }
  // test helpers
  open() {
    this.readyState = MockSocket.OPEN;
    this.onopen?.();
  }
  emit(ev: object) {
    this.onmessage?.({ data: JSON.stringify(ev) });
  }
  emitRaw(data: string) {
    this.onmessage?.({ data });
  }
  serverClose(code = 1000, wasClean = true) {
    if (this.readyState === MockSocket.CLOSED) return;
    this.readyState = MockSocket.CLOSED;
    this.onclose?.({ code, wasClean });
  }
  static get last(): MockSocket {
    return MockSocket.instances[MockSocket.instances.length - 1];
  }
}

const realWs = global.WebSocket;

/** Swap global.WebSocket for MockSocket before each test; restore it after all. */
export function installMockWebSocket() {
  beforeEach(() => {
    MockSocket.instances = [];
    (global as unknown as { WebSocket: unknown }).WebSocket = MockSocket;
  });
  afterAll(() => {
    (global as unknown as { WebSocket: unknown }).WebSocket = realWs;
  });
}
