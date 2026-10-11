/**
 * The real-time channel: one WebSocket to `/ws` that reconnects automatically after network loss or a
 * server restart, with a growing delay (IF-002, UI-060).
 */

export interface SocketLike {
  onopen: ((event: Event) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  readyState: number;
  send(data: string): void;
  close(): void;
}

export interface ConnectionOptions {
  url: string;
  onMessage: (topic: string, payload: unknown) => void;
  onConnectedChange: (connected: boolean) => void;
  createSocket?: (url: string) => SocketLike;
  setTimer?: (callback: () => void, milliseconds: number) => unknown;
  clearTimer?: (timer: unknown) => void;
}

/** Reconnect delays: 0.5 s, 1 s, 2 s, 4 s, then every 5 s. */
export function reconnectDelay(attempt: number): number {
  return Math.min(500 * 2 ** attempt, 5000);
}

const OPEN = 1;

export class Connection {
  private socket: SocketLike | null = null;
  private timer: unknown = null;
  private attempt = 0;
  private stopped = true;
  private connected = false;
  private readonly createSocket: (url: string) => SocketLike;
  private readonly setTimer: (callback: () => void, milliseconds: number) => unknown;
  private readonly clearTimer: (timer: unknown) => void;

  constructor(private readonly options: ConnectionOptions) {
    this.createSocket = options.createSocket ?? ((url) => new WebSocket(url));
    this.setTimer = options.setTimer ?? ((callback, ms) => setTimeout(callback, ms));
    this.clearTimer = options.clearTimer ?? ((timer) => clearTimeout(timer as ReturnType<typeof setTimeout>));
  }

  start(): void {
    this.stopped = false;
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    if (this.timer !== null) {
      this.clearTimer(this.timer);
      this.timer = null;
    }
    this.socket?.close();
    this.socket = null;
  }

  /** Send a command; returns `false` (and sends nothing) while disconnected. */
  send(topic: string, payload: unknown): boolean {
    if (this.socket === null || this.socket.readyState !== OPEN) {
      return false;
    }
    this.socket.send(JSON.stringify({ topic, payload }));
    return true;
  }

  /** Reports only changes, not every failed reconnect attempt. */
  private setConnected(connected: boolean): void {
    if (connected !== this.connected) {
      this.connected = connected;
      this.options.onConnectedChange(connected);
    }
  }

  private connect(): void {
    const socket = this.createSocket(this.options.url);
    this.socket = socket;
    socket.onopen = () => {
      this.attempt = 0;
      this.setConnected(true);
    };
    socket.onmessage = (event) => {
      let message: unknown;
      try {
        message = JSON.parse(String(event.data));
      } catch {
        return;
      }
      if (typeof message === "object" && message !== null && "topic" in message) {
        const { topic, payload } = message as { topic: unknown; payload: unknown };
        if (typeof topic === "string") {
          this.options.onMessage(topic, payload);
        }
      }
    };
    socket.onerror = () => {
      socket.close();
    };
    socket.onclose = () => {
      if (this.socket !== socket) {
        return;
      }
      this.socket = null;
      this.setConnected(false);
      if (!this.stopped) {
        this.timer = this.setTimer(() => {
          this.timer = null;
          this.connect();
        }, reconnectDelay(this.attempt++));
      }
    };
  }
}

/** `ws://<host>/ws` for the page's own server (`wss://` behind HTTPS). */
export function defaultUrl(location: Pick<Location, "protocol" | "host">): string {
  return `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
}
