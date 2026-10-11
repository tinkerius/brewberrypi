/** Display texts (docs/specification/09-user-interface.md). */

import type { HardwareStatus } from "./types";

const NO_VALUE = "--";

/** UI-010: `62.5°C`, `Sensor error` for an INVALID reading, `--` before the first message. */
export function formatTemperature(hardware: HardwareStatus | null): string {
  if (hardware === null) {
    return NO_VALUE;
  }
  return hardware.temperature === null ? "Sensor error" : `${hardware.temperature.toFixed(1)}°C`;
}

/** UI-010: `on` / `off`. */
export function formatPump(hardware: HardwareStatus | null): string {
  return hardware === null ? NO_VALUE : hardware.pumpstatus ? "on" : "off";
}

/** UI-010: requested power in percent, e.g. `50%`. */
export function formatHeating(hardware: HardwareStatus | null): string {
  return hardware === null ? NO_VALUE : `${Math.round(hardware.heatingstatus * 100)}%`;
}

/** UI-020: x axis ticks `HH:MM` in the browser's local time. */
export function formatTime(epochSeconds: number): string {
  const date = new Date(epochSeconds * 1000);
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** UI-021: time in the hover legend, `HH:MM:SS`. */
export function formatTimeWithSeconds(epochSeconds: number): string {
  const date = new Date(epochSeconds * 1000);
  return `${formatTime(epochSeconds)}:${pad(date.getSeconds())}`;
}

/** UI-020: y axis ticks with one decimal. */
export function formatDegrees(value: number): string {
  return value.toFixed(1);
}

/** FIX-24: a description is split at `\n` so each line is rendered as its own line. */
export function descriptionLines(description: string): string[] {
  return description.split("\n");
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}
