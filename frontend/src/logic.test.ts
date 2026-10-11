import { describe, expect, it, vi } from "vitest";
import { isAccepted } from "./commands";
import { Connection, defaultUrl, reconnectDelay, type SocketLike } from "./connection";
import { descriptionLines, formatDegrees, formatHeating, formatPump, formatTemperature, formatTime } from "./format";
import { toPlotData } from "./Chart";
import { dismissReply, initialState, receive, setConnected } from "./state";
import type { EngineState } from "./types";

describe("UI-010 hardware status texts", () => {
  it("shows -- before the first message", () => {
    expect([formatTemperature(null), formatPump(null), formatHeating(null)]).toEqual(["--", "--", "--"]);
  });

  it("shows temperature with one decimal, pump on/off and heating in percent", () => {
    const hardware = { temperature: 62, pumpstatus: true, heatingstatus: 0.5 };
    expect([formatTemperature(hardware), formatPump(hardware), formatHeating(hardware)]).toEqual(["62.0°C", "on", "50%"]);
    expect(formatHeating({ ...hardware, heatingstatus: 1 })).toBe("100%");
    expect(formatPump({ ...hardware, pumpstatus: false })).toBe("off");
  });

  it("AC-005 shows Sensor error for an INVALID reading", () => {
    expect(formatTemperature({ temperature: null, pumpstatus: true, heatingstatus: 0 })).toBe("Sensor error");
  });
});

describe("UI-020 chart formatting", () => {
  it("formats time ticks as HH:MM in local time and temperatures with one decimal", () => {
    const local = new Date(2026, 9, 11, 7, 5, 9).getTime() / 1000;
    expect(formatTime(local)).toBe("07:05");
    expect(formatDegrees(62)).toBe("62.0");
  });

  it("UI-022 has no data before the first chart message", () => {
    expect(toPlotData(null)).toEqual([[], []]);
  });

  it("converts epoch milliseconds to the plot's seconds", () => {
    const series = [{ key: "Kettle Temperature", values: [{ x: 1_718_197_200_000, y: 62.5 }] }];
    expect(toPlotData(series)).toEqual([[1_718_197_200], [62.5]]);
  });
});

describe("FIX-24 descriptions", () => {
  it("splits line breaks into lines", () => {
    expect(descriptionLines("Now it's your job to do the iodine test.\nRest at 25.0 degrees (C) for 1min.")).toEqual([
      "Now it's your job to do the iodine test.",
      "Rest at 25.0 degrees (C) for 1min.",
    ]);
  });
});

describe("UI-042 command acceptance matrix", () => {
  const states: EngineState[] = ["NoProcess", "Loaded", "Running", "Paused", "Stopped", "Finished"];
  const allowed = (command: "load" | "unload" | "start" | "pause" | "stop") =>
    states.filter((state) => isAccepted(command, state));

  it("matches spec 03 §3.2", () => {
    expect(allowed("load")).toEqual(["NoProcess", "Loaded", "Stopped", "Finished"]);
    expect(allowed("unload")).toEqual(["Loaded", "Stopped", "Finished"]);
    expect(allowed("start")).toEqual(["Loaded", "Paused"]);
    expect(allowed("pause")).toEqual(["Running"]);
    expect(allowed("stop")).toEqual(["Running", "Paused"]);
  });

  it("accepts nothing before the first process state", () => {
    expect(isAccepted("load", undefined)).toBe(false);
  });
});

describe("state", () => {
  it("stores the latest broadcast of each topic", () => {
    let state = receive(initialState, "/hardware/status", { temperature: 20, pumpstatus: false, heatingstatus: 0 });
    state = receive(state, "/process/state", { state: "NoProcess" });
    state = receive(state, "/process/recipes", [{ id: "ZORA", name: "München 12.6 - SUD1:ZORA" }]);
    state = receive(state, "/unknown", 1);
    expect(state.hardware?.temperature).toBe(20);
    expect(state.process).toEqual({ state: "NoProcess" });
    expect(state.recipes).toHaveLength(1);
    expect(state.chart).toBeNull();
  });

  it("AC-076 queues every reply for the Information modal until confirmed", () => {
    let state = receive(initialState, "/process/reply", { command: "load", success: true, message: "first" });
    state = receive(state, "/process/reply", { command: "start", success: false, message: "second" });
    expect(state.replies.map((reply) => reply.message)).toEqual(["first", "second"]);
    state = dismissReply(state);
    expect(state.replies.map((reply) => reply.message)).toEqual(["second"]);
    expect(setConnected(state, true).connected).toBe(true);
  });
});

class FakeSocket implements SocketLike {
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readyState = 0;
  sent: string[] = [];
  closed = false;

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.closed = true;
    this.readyState = 3;
    this.onclose?.({} as CloseEvent);
  }

  open(): void {
    this.readyState = 1;
    this.onopen?.({} as Event);
  }

  receive(data: string): void {
    this.onmessage?.({ data } as MessageEvent);
  }
}

function setup() {
  const sockets: FakeSocket[] = [];
  const timers: { callback: () => void; ms: number }[] = [];
  const messages: [string, unknown][] = [];
  const connected: boolean[] = [];
  const connection = new Connection({
    url: "ws://pi:8080/ws",
    onMessage: (topic, payload) => messages.push([topic, payload]),
    onConnectedChange: (value) => connected.push(value),
    createSocket: () => {
      const socket = new FakeSocket();
      sockets.push(socket);
      return socket;
    },
    setTimer: (callback, ms) => timers.push({ callback, ms }),
    clearTimer: vi.fn(),
  });
  return { connection, sockets, timers, messages, connected };
}

describe("UI-060 connection", () => {
  it("builds the WebSocket URL of the page's server", () => {
    expect(defaultUrl({ protocol: "http:", host: "brewberrypi:8080" })).toBe("ws://brewberrypi:8080/ws");
    expect(defaultUrl({ protocol: "https:", host: "pi" })).toBe("wss://pi/ws");
  });

  it("delivers messages and sends commands as {topic, payload}", () => {
    const { connection, sockets, messages, connected } = setup();
    connection.start();
    expect(connection.send("/service/process/start", {})).toBe(false); // not open yet
    sockets[0].open();
    sockets[0].receive('{"topic": "/process/state", "payload": {"state": "NoProcess"}}');
    sockets[0].receive("not json");
    expect(messages).toEqual([["/process/state", { state: "NoProcess" }]]);
    expect(connected).toEqual([true]);
    expect(connection.send("/service/process/load", { recipe: "ZORA" })).toBe(true);
    expect(sockets[0].sent).toEqual(['{"topic":"/service/process/load","payload":{"recipe":"ZORA"}}']);
  });

  it("AC-077 reconnects after the server went away, with growing delays", () => {
    const { connection, sockets, timers, connected } = setup();
    connection.start();
    sockets[0].open();
    sockets[0].close(); // server stopped
    expect(connected).toEqual([true, false]);
    expect(timers.map((timer) => timer.ms)).toEqual([500]);
    timers[0].callback();
    sockets[1].close(); // still down
    timers[1].callback();
    expect(timers.map((timer) => timer.ms)).toEqual([500, 1000]);
    sockets[2].open(); // server back
    expect(connected).toEqual([true, false, true]);
    sockets[2].close();
    expect(timers[2].ms).toBe(500); // delay starts again after a successful connection
  });

  it("caps the reconnect delay at 5 s", () => {
    expect([0, 1, 2, 3, 4, 10].map(reconnectDelay)).toEqual([500, 1000, 2000, 4000, 5000, 5000]);
  });

  it("does not reconnect after stop", () => {
    const { connection, sockets, timers } = setup();
    connection.start();
    sockets[0].open();
    connection.stop();
    expect(timers).toEqual([]);
  });
});
