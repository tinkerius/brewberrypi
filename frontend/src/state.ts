/** UI state built from the event stream and the command replies. */

import type {
  ChartSeries,
  ChartUpdate,
  CommandReply,
  EventName,
  HardwareStatus,
  ProcessState,
  Recipe,
  Snapshot,
} from "./types";

export interface AppState {
  connected: boolean;
  /** `null` until the first snapshot (UI-010 `--`, UI-022 empty chart, UI-040 "loading…"). */
  hardware: HardwareStatus | null;
  process: ProcessState | null;
  recipes: Recipe[] | null;
  chart: ChartSeries[] | null;
  /** Replies waiting to be shown in the Information modal, oldest first (UI-050). */
  replies: CommandReply[];
}

export const initialState: AppState = {
  connected: false,
  hardware: null,
  process: null,
  recipes: null,
  chart: null,
  replies: [],
};

export function receive(state: AppState, name: EventName, data: unknown): AppState {
  switch (name) {
    case "snapshot": {
      const snapshot = data as Snapshot;
      return {
        ...state,
        hardware: snapshot.hardware,
        process: snapshot.process,
        recipes: snapshot.recipes,
        chart: snapshot.chart,
      };
    }
    case "hardware":
      return { ...state, hardware: data as HardwareStatus };
    case "process":
      return { ...state, process: data as ProcessState };
    case "recipes":
      return { ...state, recipes: data as Recipe[] };
    case "chart":
      return { ...state, chart: applyChartUpdate(state.chart, data as ChartUpdate) };
    default:
      return state; // ping
  }
}

/** IF-073: drop the thinned points, append the new one. */
export function applyChartUpdate(chart: ChartSeries[] | null, update: ChartUpdate): ChartSeries[] | null {
  if (chart === null || chart.length === 0) {
    return chart;
  }
  const removed = new Set(update.remove);
  const [series, ...rest] = chart;
  return [{ ...series, values: [...series.values.filter((point) => !removed.has(point.x)), update.add] }, ...rest];
}

export function setConnected(state: AppState, connected: boolean): AppState {
  return { ...state, connected };
}

export function addReply(state: AppState, reply: CommandReply): AppState {
  return { ...state, replies: [...state.replies, reply] };
}

/** Close the Information modal: the next queued reply, if any, is shown next. */
export function dismissReply(state: AppState): AppState {
  return { ...state, replies: state.replies.slice(1) };
}
