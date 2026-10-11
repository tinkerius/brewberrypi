/** UI state built from the server's broadcasts and replies. */

import { type ChartSeries, type CommandReply, type HardwareStatus, type ProcessState, type Recipe, TOPICS } from "./types";

export interface AppState {
  connected: boolean;
  /** `null` until the first message of the topic (UI-010 `--`, UI-022 empty chart, UI-040 "loading…"). */
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

export function receive(state: AppState, topic: string, payload: unknown): AppState {
  switch (topic) {
    case TOPICS.hardwareStatus:
      return { ...state, hardware: payload as HardwareStatus };
    case TOPICS.processState:
      return { ...state, process: payload as ProcessState };
    case TOPICS.recipes:
      return { ...state, recipes: payload as Recipe[] };
    case TOPICS.chart:
      return { ...state, chart: payload as ChartSeries[] };
    case TOPICS.reply:
      return { ...state, replies: [...state.replies, payload as CommandReply] };
    default:
      return state;
  }
}

export function setConnected(state: AppState, connected: boolean): AppState {
  return { ...state, connected };
}

/** Close the Information modal: the next queued reply, if any, is shown next. */
export function dismissReply(state: AppState): AppState {
  return { ...state, replies: state.replies.slice(1) };
}
