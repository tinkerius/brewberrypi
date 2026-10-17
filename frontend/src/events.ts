/**
 * The event stream (IF-070..076): one EventSource on `/api/events`. Every (re)connection starts with a
 * `snapshot`; the UI counts as connected from then on (UI-060). The browser reconnects by itself after a lost
 * connection; a missing heartbeat (IF-074) or a stream the browser gave up on is reopened here, with a
 * growing delay.
 */

import { EVENTS, type EventName } from "./types";

export interface SourceLike {
  readyState: number;
  onerror: ((event: Event) => void) | null;
  addEventListener(type: string, listener: (event: MessageEvent) => void): void;
  close(): void;
}

export interface EventStreamOptions {
  url: string;
  onEvent: (name: EventName, data: unknown) => void;
  onConnectedChange: (connected: boolean) => void;
  createSource?: (url: string) => SourceLike;
  setTimer?: (callback: () => void, milliseconds: number) => unknown;
  clearTimer?: (timer: unknown) => void;
}

/** Reopen delays: 0.5 s, 1 s, 2 s, 4 s, then every 5 s. */
export function reconnectDelay(attempt: number): number {
  return Math.min(500 * 2 ** attempt, 5000);
}

/** Missed heartbeats after which the connection counts as dead. */
export const MISSED_HEARTBEATS = 2.5;
const CLOSED = 2;

export class EventStream {
  private source: SourceLike | null = null;
  private reopenTimer: unknown = null;
  private watchdog: unknown = null;
  private heartbeat = 5000;
  private attempt = 0;
  private stopped = true;
  private connected = false;
  private readonly createSource: (url: string) => SourceLike;
  private readonly setTimer: (callback: () => void, milliseconds: number) => unknown;
  private readonly clearTimer: (timer: unknown) => void;

  constructor(private readonly options: EventStreamOptions) {
    this.createSource = options.createSource ?? ((url) => new EventSource(url));
    this.setTimer = options.setTimer ?? ((callback, ms) => setTimeout(callback, ms));
    this.clearTimer = options.clearTimer ?? ((timer) => clearTimeout(timer as ReturnType<typeof setTimeout>));
  }

  start(): void {
    this.stopped = false;
    this.open();
  }

  stop(): void {
    this.stopped = true;
    this.cancelTimers();
    this.source?.close();
    this.source = null;
  }

  private open(): void {
    const source = this.createSource(this.options.url);
    this.source = source;
    for (const name of EVENTS) {
      source.addEventListener(name, (event) => {
        if (this.source === source) {
          this.receive(name, event.data);
        }
      });
    }
    source.onerror = () => {
      if (this.source !== source) {
        return;
      }
      this.setConnected(false);
      if (source.readyState === CLOSED) {
        this.reopen(); // the browser gave up (e.g. an error status during a restart)
      }
      // otherwise the browser reconnects by itself and the server sends a new snapshot
    };
  }

  private receive(name: EventName, text: unknown): void {
    let data: unknown;
    try {
      data = JSON.parse(String(text));
    } catch {
      return;
    }
    if (name === "snapshot") {
      const heartbeat = (data as { heartbeatMilliseconds?: unknown }).heartbeatMilliseconds;
      if (typeof heartbeat === "number" && heartbeat > 0) {
        this.heartbeat = heartbeat;
      }
      this.attempt = 0;
      this.setConnected(true);
    }
    if (this.connected) {
      this.armWatchdog();
      this.options.onEvent(name, data);
    }
  }

  private armWatchdog(): void {
    if (this.watchdog !== null) {
      this.clearTimer(this.watchdog);
    }
    this.watchdog = this.setTimer(() => {
      this.watchdog = null;
      this.setConnected(false);
      this.reopen(); // no event, not even a ping: the connection is dead
    }, this.heartbeat * MISSED_HEARTBEATS);
  }

  private reopen(): void {
    this.source?.close();
    this.source = null;
    this.cancelTimers();
    if (this.stopped) {
      return;
    }
    this.reopenTimer = this.setTimer(() => {
      this.reopenTimer = null;
      this.open();
    }, reconnectDelay(this.attempt++));
  }

  private cancelTimers(): void {
    for (const timer of [this.reopenTimer, this.watchdog]) {
      if (timer !== null) {
        this.clearTimer(timer);
      }
    }
    this.reopenTimer = null;
    this.watchdog = null;
  }

  /** Reports only changes, not every failed attempt. */
  private setConnected(connected: boolean): void {
    if (connected !== this.connected) {
      this.connected = connected;
      this.options.onConnectedChange(connected);
    }
  }
}
