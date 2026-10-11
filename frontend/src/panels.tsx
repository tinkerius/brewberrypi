/** Page parts without the chart (docs/specification/09-user-interface.md §9.1, §9.2, §9.4, §9.5, §9.7). */

import { useEffect, useRef } from "preact/hooks";
import { isAccepted } from "./commands";
import { descriptionLines, formatHeating, formatPump, formatTemperature } from "./format";
import type { CommandName, EngineState, Goal, HardwareStatus, ProcessState, Recipe } from "./types";

export type SendCommand = (command: CommandName, payload?: Record<string, string>) => void;

/** Navbar title and page title (§9.1). */
export const APP_TITLE = "Brewberry Pi";

/** UI-060: non-blocking connection indicator. */
export function ConnectionIndicator(props: { connected: boolean; everConnected: boolean }) {
  if (props.connected) {
    return null;
  }
  return (
    <div class="connection" role="status">
      {props.everConnected ? "disconnected — reconnecting…" : "connecting…"}
    </div>
  );
}

export function Panel(props: { title: string; stale?: boolean; children: preact.ComponentChildren }) {
  return (
    <section class={props.stale ? "panel stale" : "panel"}>
      <h2 class="panel-heading">{props.title}</h2>
      <div class="panel-body">{props.children}</div>
    </section>
  );
}

/** UI-010, UI-011. */
export function HardwareStatusPanel(props: { hardware: HardwareStatus | null; state: EngineState | undefined; stale: boolean }) {
  const { hardware } = props;
  return (
    <Panel title="Hardware Status" stale={props.stale}>
      <dl class="status">
        <div>
          <dt>Temperature:</dt>
          <dd class={hardware !== null && hardware.temperature === null ? "sensor-error" : undefined}>
            {formatTemperature(hardware)}
          </dd>
        </div>
        <div>
          <dt>Pump:</dt>
          <dd>{formatPump(hardware)}</dd>
        </div>
        <div>
          <dt>Heating:</dt>
          <dd>{formatHeating(hardware)}</dd>
        </div>
        <div>
          <dt>Process:</dt>
          <dd>{props.state ?? "--"}</dd>
        </div>
      </dl>
    </Panel>
  );
}

const GOAL_CLASS: Record<Goal["status"], string> = { Done: "goal goal-done", Active: "goal goal-active", Waiting: "goal" };

/** UI-031, UI-032. */
export function GoalItem(props: { goal: Goal; connected: boolean; onRespond: (option: string) => void }) {
  const { goal } = props;
  return (
    <li class={GOAL_CLASS[goal.status]}>
      <span class="badge">{goal.status}</span>
      <h3>{goal.name}</h3>
      <p class="description">
        {descriptionLines(goal.description).map((line, index) => (
          <span key={index}>
            {index > 0 && <br />}
            {line}
          </span>
        ))}
      </p>
      {goal.status === "Active" && (
        <div class="progress" role="progressbar" aria-valuenow={goal.statuspercent} aria-valuemin={0} aria-valuemax={100}>
          <div class="progress-bar" style={{ width: `${goal.statuspercent}%` }} />
          <span class="progress-label">{goal.statusmessage}</span>
        </div>
      )}
      {goal.activeRequest && (
        <div class="request">
          <p>{goal.activeRequest.message}</p>
          {goal.activeRequest.options.map((option) => (
            <button key={option} type="button" class="btn btn-primary" disabled={!props.connected} onClick={() => props.onRespond(option)}>
              {option}
            </button>
          ))}
        </div>
      )}
    </li>
  );
}

/** UI-030..033 and the process controls UI-040..043. */
export function ProcessPanel(props: {
  process: ProcessState | null;
  recipes: Recipe[] | null;
  connected: boolean;
  send: SendCommand;
  onStop: () => void;
}) {
  const { process, connected, send } = props;
  const state = process?.state;
  const goals = process !== null && "goals" in process ? process.goals : [];
  const activeIndex = goals.findIndex((goal) => goal.status === "Active");
  const list = useRef<HTMLOListElement>(null);

  useEffect(() => {
    // UI-033: bring the active goal into view when another goal becomes active.
    const item = list.current?.children[activeIndex] as HTMLElement | undefined;
    item?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [activeIndex]);

  const enabled = (command: Exclude<CommandName, "respond">) => connected && isAccepted(command, state);

  return (
    <Panel title="Brewing Process" stale={!connected}>
      {process !== null && "processname" in process && <h3 class="process-name">{process.processname}</h3>}
      <ol class="goals" ref={list}>
        {goals.map((goal, index) => (
          <GoalItem key={index} goal={goal} connected={connected} onRespond={(option) => send("respond", { response: option })} />
        ))}
      </ol>
      <div class="controls">
        <select
          aria-label="Load Process"
          disabled={!enabled("load") || props.recipes === null}
          value=""
          onChange={(event) => {
            const id = (event.target as HTMLSelectElement).value;
            if (id) {
              send("load", { recipe: id });
            }
          }}
        >
          <option value="">{props.recipes === null ? "loading…" : "Load Process"}</option>
          {props.recipes?.map((recipe) => (
            <option key={recipe.id} value={recipe.id}>
              {recipe.name}
            </option>
          ))}
        </select>
        <button type="button" class="btn" disabled={!enabled("unload")} onClick={() => send("unload")}>
          Unload Process
        </button>
      </div>
      <div class="controls">
        <button type="button" class="btn" disabled={!enabled("start")} onClick={() => send("start")}>
          Start Process
        </button>
        <button type="button" class="btn" disabled={!enabled("pause")} onClick={() => send("pause")}>
          Pause Process
        </button>
        <button type="button" class="btn btn-danger" disabled={!enabled("stop")} onClick={props.onStop}>
          Stop Process
        </button>
      </div>
    </Panel>
  );
}
