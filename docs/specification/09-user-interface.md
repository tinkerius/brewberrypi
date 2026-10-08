# 09 — User Interface

Single-page web application served by the BrewberryPi server at `/` (`index`).
Responsive (usable on phone, tablet and desktop). Language of UI texts: English
(legacy); recipe texts as defined in the recipe file.

## 9.1 Layout (top to bottom)

```text
┌──────────────────────────────────────────────────────────────┐
│ Brewberry Pi                                   (dark top bar) │
├──────────────────────────────────────────────────────────────┤
│ [Hardware Status]                                             │
│  Temperature: 62.5°C   Pump: on   Heating: 50%   Process: …   │
├──────────────────────────────────────────────────────────────┤
│ [Chart]                                                       │
│  line chart "Kettle Temperature" over time (height ≈ 300 px)  │
├──────────────────────────────────────────────────────────────┤
│ [Brewing Process]                                             │
│  <process name>                                               │
│  ┌ goal list item (one per goal) ───────────────────────────┐ │
│  │ Heat Up                                      [Active]    │ │
│  │ Heat up mash to 62.0 degrees (C).                        │ │
│  │ [██████████░░░░░░░░░ 50%]                                │ │
│  │ Iodine test successfull?  [Yes] [No]                     │ │
│  └──────────────────────────────────────────────────────────┘ │
│  [Load Process ▾] [Unload Process]                            │
│  [Start Process] [Pause Process] [Stop Process]               │
└──────────────────────────────────────────────────────────────┘
          (modal "Information" with [Confirm] for replies)
```

Legacy look: Bootstrap 3 panels ("panel-primary") with blue headers, dark navbar
titled **Brewberry Pi**. Page title: `Brewberry Pi`. A visual refresh is allowed
as long as all elements and behaviours below are kept.

## 9.2 Hardware Status panel

- `UI-010` Shows, updated live from `/hardware/status`:
  - `Temperature: <t>°C` — one decimal; `--` before the first message; **`Sensor error`** when `temperature` is `null` `[FIX-02]`.
  - `Pump: on|off` — `--` before first message.
  - `Heating: <p·100>%` — e.g. `0%`, `50%`, `100%`; `--` before first message.
- `UI-011` `[NEW, FIX-20]` Shows the engine state (`NoProcess`, `Loaded`, `Running`, `Paused`, `Stopped`, `Finished`) from `/process/state` (e.g. as a label next to the process name or in this panel).

## 9.3 Chart panel

- `UI-020` Line chart of `/process/chart` data: x axis labelled `Time`, ticks formatted `HH:MM` (local time of the browser); y axis labelled `Temperature`, ticks with 1 decimal; one series `Kettle Temperature`.
- `UI-021` Interactive guideline/tooltip on hover showing time and temperature.
- `UI-022` Before the first chart message, the chart is **empty** (legacy showed hard-coded demo data with a fake target profile). `[FIX-17]`
- `UI-023` The chart updates without resetting user interaction more than necessary (legacy re-rendered on every update).

## 9.4 Brewing Process panel

- `UI-030` Heading: `processname` of the loaded process; nothing when no process is loaded.
- `UI-031` One list item per goal, in order, showing:
  - badge with the goal `status` (`Waiting`/`Active`/`Done`);
  - `name` as heading;
  - `description` — line breaks (`\n`) rendered as line breaks `[FIX-24]`;
  - colour: `Done` → green (success), `Active` → yellow/amber (warning), `Waiting` → neutral;
  - **progress bar** only for the `Active` goal: width = `statuspercent` %, label = `statusmessage`;
  - if `activeRequest` exists: its `message` and **one button per option** (label = option text).
- `UI-032` Clicking an option button sends `/service/process/request` with `{ "response": "<option text>" }`.
- `UI-033` The active goal SHOULD be scrolled into view / visually emphasised (long recipes have 11 goals).

## 9.5 Process controls

- `UI-040` **Load Process** dropdown: one entry per recipe from `/process/recipes` (label = `name`); selecting sends `/service/process/load` with `{ "recipe": "<id>" }`. Before the first recipe list arrives, the dropdown is empty / shows "loading…" (legacy showed a hard-coded list of 3 recipes). `[FIX-17]`
- `UI-041` Buttons **Unload Process**, **Start Process**, **Pause Process**, **Stop Process** send the corresponding commands (empty payload).
- `UI-042` `[NEW]` Buttons SHOULD be disabled when the command is not accepted in the current engine state (matrix in [03](03-brew-process-engine.md)). The server remains authoritative.
- `UI-043` `[NEW]` **Stop Process** SHOULD ask for confirmation ("Stop the running process? Heating and pump will be switched off.") because a stopped process cannot be resumed.

## 9.6 Information modal

- `UI-050` Every command reply (`IF-050`) is shown in a modal dialog titled **Information** with the reply `message` and a **Confirm** button that closes it. `[FIX-15]`
  (Phase 2 MAY show successful replies as a non-blocking toast and only errors as modal — see `Q-11`.)

## 9.7 Connection handling

- `UI-060` On connection failure the UI shows a clear, non-blocking "disconnected — reconnecting…" indicator and reconnects automatically (legacy: `alert('sad')` on failed handshake).
- `UI-061` While disconnected, displayed values are marked as stale and command buttons are disabled.

## 9.8 Assets

- `UI-070` The UI MUST work without internet access (all scripts, styles and fonts are served locally by the Pi). The legacy page referenced two CDN scripts only for IE < 9; these are not required.
