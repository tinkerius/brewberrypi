/**
 * Messages of the client/server interface (docs/specification/08-client-server-interface.md,
 * docs/specification/data/messages.schema.json). Every WebSocket message is `{ topic, payload }`.
 */

export const TOPICS = {
  hardwareStatus: "/hardware/status",
  processState: "/process/state",
  recipes: "/process/recipes",
  chart: "/process/chart",
  reply: "/process/reply",
} as const;

export type CommandName = "load" | "unload" | "start" | "pause" | "stop" | "respond";

export const COMMAND_TOPICS: Record<CommandName, string> = {
  load: "/service/process/load",
  unload: "/service/process/unload",
  start: "/service/process/start",
  pause: "/service/process/pause",
  stop: "/service/process/stop",
  respond: "/service/process/request",
};

/** IF-010. `temperature` is `null` when the sensor reading is INVALID. */
export interface HardwareStatus {
  temperature: number | null;
  pumpstatus: boolean;
  heatingstatus: number;
}

export type EngineState = "NoProcess" | "Loaded" | "Running" | "Paused" | "Stopped" | "Finished";
export type GoalStatus = "Waiting" | "Active" | "Done";

export interface OperatorRequest {
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
export interface ChartSeries {
  key: string;
  values: { x: number; y: number }[];
}

/** IF-050. */
export interface CommandReply {
  command: CommandName;
  success: boolean;
  message: string;
}
