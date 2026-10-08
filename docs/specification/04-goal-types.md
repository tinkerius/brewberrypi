# 04 — Goal Types

Every goal implements `pursue()` which is called once per engine tick while the
goal is `Active` (`ENG-020`). `pursue()` returns `true` when the goal is achieved.
The building blocks `holdTemperature(...)` and `countdown(...)` are defined in
[05 — Temperature Control](05-temperature-control.md).

Temperature values in generated texts are formatted with **one decimal place**
(`62.0`), as the legacy system did (Java float formatting). Minutes are integers.

## 4.1 Overview

| GoalType | Name (display) | Description (display) | Parameters | Controls temperature | Operator request | Progress source |
|---|---|---|---|---|---|---|
| `PourInBrewingWater` | `Add Water` | `Pour in the brewing water.` | – | no | Confirmation `Pour in brewing water` | default (0 %) |
| `HeatUp` | `Heat Up` | `Heat up mash to <T> degrees (C).` | `temperature` | yes (hysteresis) | – | temperature |
| `MashIn` | `Mash In` | `Now it's your job to mash in the malt.` | – | no | Confirmation `Mash in now` | default (0 %) |
| `Rest` | `Rest` *or custom* | `Rest at <T> degrees (C) for <M>min.` *or custom* | `temperature`, `minutes`, optional `name`, `description` | yes (hysteresis) | – | time |
| `IodineTest` | `Iodine Test` | `Now it's your job to do the iodine test.` (+ appended lines) | `temperature`, `minutes` | yes (hysteresis) `[FIX-13]` | Yes/No `Iodine test successfull?` | time (additional rest) |
| `Lautering` | `Lautering` | `Now it's your job to lauter.` | – | all off | Confirmation `Lauter now` | default (0 %) |
| `HeatUpForHopsCooking` | `Heat Up` | `Heat up mash for cooking` | – (fixed target 97.0 °C) | yes (**heat boost**) | – | temperature |
| `CookWater` | *custom* | *custom* | `name`, `description`, `minutes` (fixed target 100.0 °C) | yes (hysteresis) | – | time |

> The request text `Iodine test successfull?` contains a legacy spelling mistake.
> Whether to keep it is listed in [13](13-open-questions.md) (`Q-07`). Until decided, keep the legacy text.

## 4.2 Goal behaviour

### `GOAL-001` PourInBrewingWater
1. If no request is active: create `ConfirmationRequest("Pour in brewing water")` (starts reminder beeps, `DOM-033`).
2. Return `true` when the request is confirmed, else `false`.
- Actuators are **not** changed by this goal (they stay as left by the previous goal / initial off state).

### `GOAL-002` HeatUp(T)
1. `reached = holdTemperature(T, boost=false)` (`CTL-010`) — switches the pump on and regulates the heater.
2. Progress = temperature progress (`CTL-020`).
3. Return `reached` (current temperature ≥ T).
- On the achieving tick the hysteresis controller has already switched the heater **off** (because current ≥ T), so the next goal starts with the heater off.

### `GOAL-003` MashIn
Same as `GOAL-001` with request text `Mash in now`.
- Actuators are not changed: the pump typically stays **on** (from the previous HeatUp), the heater is off. The temperature is **not** held while waiting (legacy behaviour; see `Q-03`).

### `GOAL-004` Rest(T, M[, name, description])
Each tick:
1. `holdTemperature(T, boost=false)` (result ignored).
2. `elapsed = countdown(M)` (`CTL-030`); the countdown starts on the **first tick** of this goal, regardless of the current temperature.
3. Progress = time progress (`CTL-031`).
4. Return `elapsed`.

### `GOAL-005` IodineTest(T, M)
The goal has two phases: **asking** (initial) and **additional rest**.

*Asking phase* (each tick):
1. `holdTemperature(T, boost=false)` — **new**: keep the mash at T while the brewer performs the test. `[FIX-13]`
   (Legacy did nothing here, leaving the heater in whatever state the previous Rest's last tick left it — possibly *on* indefinitely.)
2. If no request is active: create `YesNoDecisionRequest("Iodine test successfull?")`.
3. If answered **Yes** → return `true` (goal done).
4. If answered **No** →
   - remove the request (reminders stop),
   - switch to *additional rest* phase,
   - append a line to `description`: `"\nRest at <T> degrees (C) for <M>min."` (appended again on every further *No*; legacy behaviour),
   - return `false`.
5. Otherwise return `false`.

*Additional rest phase* (each tick):
1. `holdTemperature(T, boost=false)`.
2. `elapsed = countdown(M)` (starts on first tick of this phase).
3. If `elapsed`: reset the countdown (next additional rest starts fresh) and switch back to *asking* phase (a new request is created on the next tick). Return `false`.

Progress:
- `statusPercent` = time progress while in *additional rest*, else `0`.
- `statusMessage` = time message (`MM:SS left`) while in *additional rest*; in *asking* phase `"Waiting for answer"`. `[FIX-14]` (legacy: undefined/empty in the first asking phase, stale last timer text after an additional rest)

### `GOAL-006` Lautering
Each tick:
1. **Switch everything off** (heating 0, pump off).
2. If no request is active: create `ConfirmationRequest("Lauter now")`.
3. Return `true` when confirmed.

### `GOAL-007` HeatUpForHopsCooking
1. `reached = holdTemperature(97.0, boost=true)` — heat boost: heater always at full power (1.0) until reached, pump on.
2. Progress = temperature progress.
3. Return `reached` (current ≥ 97.0).
- Note: on the achieving tick the heater is left at **1.0** (boost does not switch off). The next goal (typically CookWater) takes over; if it is the last goal, the engine switches everything off (`ENG-025`).

### `GOAL-008` CookWater(name, description, M)
Identical to `Rest` with fixed target temperature **100.0 °C**.
- Consequence (legacy behaviour, keep): since water boils at ≤ 100 °C, the target is normally never reached; because the distance to target is < 3 °C above 97 °C, the heater runs at **50 %** duty cycle during the boil (see `CTL-012`, question `Q-04`).

## 4.3 Extensibility

- `GOAL-100` Goal types are selected by the `type` field of a recipe goal definition ([07](07-recipes.md)). Adding a new goal type MUST NOT require changes to the engine loop.
