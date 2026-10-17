/**
 * Messages of the client/server interface (docs/specification/08-client-server-interface.md,
 * docs/specification/data/messages.schema.json): REST under `/api`, server-sent events at `/api/events`.
 */

export type CommandName = "load" | "unload" | "start" | "pause" | "resume" | "stop" | "respond";

/** Event names of the event stream (IF-070). */
export const EVENTS = ["snapshot", "hardware", "process", "recipes", "chart", "ping"] as const;
export type EventName = (typeof EVENTS)[number];

/** IF-010. `temperature` is `null` when the sensor reading is INVALID. */
export interface HardwareStatus {
  temperature: number | null;
  pumpstatus: boolean;
  heatingstatus: number;
}

export type EngineState = "NoProcess" | "Loaded" | "Running" | "Paused" | "Stopped" | "Finished";
export type GoalStatus = "Waiting" | "Active" | "Done";

export interface OperatorRequest {
  /** Answer it with POST /api/process/requests/{id} (DOM-035). */
  id: string;
  message: string;
  options: string[];
}

export interface Goal {
  name: string;
  description: string;
  status: GoalStatus;
  statuspercent: number;
  statusmessage: string;
  activeRequest?: OperatorRequest;
}

/** IF-020. */
export type ProcessState =
  | { state: "NoProcess" }
  | {
      processid: string;
      processname: string;
      state: Exclude<EngineState, "NoProcess">;
      goals: Goal[];
    };

/** IF-030. */
export interface Recipe {
  id: string;
  name: string;
}

/** IF-040: x in epoch milliseconds, y in °C. */
export interface ChartPoint {
  x: number;
  y: number;
}

export interface ChartSeries {
  key: string;
  values: ChartPoint[];
}

/** IF-073: a new point and the x of each point that thinning removed. */
export interface ChartUpdate {
  add: ChartPoint;
  remove: number[];
}

/** IF-071: the first event of every stream. */
export interface Snapshot {
  hardware: HardwareStatus;
  process: ProcessState;
  recipes: Recipe[];
  chart: ChartSeries[];
  heartbeatMilliseconds: number;
}

/** IF-050: the reply to a command, shown in the Information modal (UI-050). */
export interface CommandReply {
  command: CommandName;
  success: boolean;
  message: string;
}
