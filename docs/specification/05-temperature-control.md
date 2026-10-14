# 05 — Temperature Control

## 5.1 Constants (defaults; all configurable, see `data/config.example.json`)

| Name | Default | Config key | Meaning |
|---|---|---|---|
| Hysteresis upper offset | `0.0` K | `control.hysteresisUpperOffset` | Offset to target while heater is **on** |
| Hysteresis lower offset | `-0.1` K | `control.hysteresisLowerOffset` | Offset to target while heater is **off** |
| Near-target band | `3.0` K | `control.nearTargetBand` | Below this distance, heat with reduced power |
| Near-target power | `0.5` | `control.nearTargetPower` | Heating power inside the near-target band |
| Full power | `1.0` | – | Heating power outside the band / during boost |
| Minimum duty phase | `10000` ms | `hardware.heating.minPhaseMilliseconds` | Shortest on- or off-phase of the duty cycle `[FIX-26]` |

## 5.2 `holdTemperature(T, boost)` — hysteresis controller

- `CTL-010` Called once per tick by temperature-controlling goals. Steps:

```text
hal.switchOnPump()                                  # pump always on while controlling
current = hal.getTemperature()
if current is INVALID:                              # [FIX-02]
    hal.setHeating(0)
    statusMessage = "Sensor error"                  # progress percent unchanged
    return false
if startTemperature not yet captured:
    startTemperature = current                      # once per goal instance
update temperature progress (CTL-020)

if boost:
    hal.setHeating(1.0)
else:
    if hal.getHeatingStatus() > 0:                  # heater currently on (any power)
        switchPoint = T + hysteresisUpperOffset     # = T
    else:
        switchPoint = T + hysteresisLowerOffset     # = T - 0.1
    if current < switchPoint:
        if (T - current) < nearTargetBand:          # < 3.0 K
            hal.setHeating(nearTargetPower)         # 0.5
        else:
            hal.setHeating(1.0)
    else:
        hal.setHeating(0)

return current >= T
```

- `CTL-011` Resulting behaviour (default constants): while heating, the heater stays on until `current ≥ T`; once off, it switches on again only when `current < T − 0.1`. This avoids relay chatter around the target.
- `CTL-012` Within 3 K below the target the heater runs at **50 % power** (duty cycle); further away at 100 %. (Boundary: distance exactly 3.0 K → full power.)
- `CTL-013` **Heat boost** (used only by `HeatUpForHopsCooking`): the heater is set to 1.0 on every tick regardless of distance or hysteresis.
- `CTL-014` The controller does not cool actively. If `current > T`, it simply keeps the heater off.
- `CTL-015` Every call logs (debug level) target, current temperature, switch point and decision (legacy logged at info level each tick).

## 5.3 Temperature progress

- `CTL-020` Per goal instance, with `start = startTemperature`, `total = T − start`, `remaining = T − current`:

```text
if total <= 0:                       # started at/above target      [FIX-14]
    percent = (current >= T) ? 100 : 0
else:
    percent = truncate( (total - remaining) * 100 / total )
percent = clamp(percent, 0, 100)                                     # [FIX-14]
statusMessage = percent + "%"        # e.g. "50%"
```

  Example: start 20.0, T 62.0, current 41.0 → total 42, remaining 21 → **50 %** → `"50%"`.
  (Legacy: division by zero when start == T; negative or >100 values possible.)

## 5.4 Countdown (time range)

- `CTL-030` `countdown(M minutes)` — per goal (or per iodine additional-rest phase):
  - starts on the first call; measures **running** time only (`ENG-030`);
  - `remaining = M·60 000 ms − elapsedRunningMs`;
  - returns `true` when `remaining ≤ 0`.
  - `M = 0` → elapsed immediately.
- `CTL-031` Time progress:

```text
percent = clamp( truncate( (duration - remaining) * 100 / duration ), 0, 100 )   # duration>0, else 100
shown   = max(remaining, 0)
statusMessage = format("%02d:%02d left", floor(shown / 60000), floor(shown / 1000) mod 60)
```

  Examples: 10-min rest, 4 min elapsed → `40`, `"06:00 left"`; 110-min rest at start → `0`, `"110:00 left"`.
  (Legacy: no zero padding — `"6:0 left"` — and negative values after expiry. `[FIX-14]`)

## 5.5 Heating power actuation (duty cycle)

The controller only requests a **heating power** `p ∈ [0, 1]`. The HAL turns it
into relay switching:

- `CTL-040` `p ≤ 0` → relay permanently **off**.
- `CTL-041` `p ≥ 1` → relay permanently **on**.
- `CTL-042` `0 < p < 1` → **time-proportional duty cycle** with `MIN = minPhaseMilliseconds` (10 000 ms) `[FIX-26]`:

```text
if p < 0.5:
    onPhase  = MIN
    offPhase = round( MIN / p - MIN )
else:
    offPhase = MIN
    onPhase  = round( MIN / (1 - p) - MIN )
repeat: relay on for onPhase, relay off for offPhase
```

| p | on (s) | off (s) | period (s) |
|---|---|---|---|
| 0.10 | 10 | 90 | 100 |
| 0.25 | 10 | 30 | 40 |
| 0.50 | 10 | 10 | 20 |
| 0.75 | 30 | 10 | 40 |
| 0.90 | 90 | 10 | 100 |

  (Legacy: `MIN` = 500 ms, so at 50 % the relay switched about once per second, which wears a mechanical relay
  out quickly (`Q-26`). The longer phases never delay switching the heater off: `CTL-040`, `CTL-044`.)

- `CTL-043` Setting the **same** power again does not restart the cycle (legacy). A **different** power in (0,1) restarts the cycle with an on-phase.
- `CTL-044` Transitions MUST be atomic: after `setHeating(p)` returns, the relay state MUST correspond to `p` (for 0/1) or to the new cycle (for 0<p<1). A previously running cycle MUST NOT switch the relay after the new power has been applied. `[FIX-03]`
  (Legacy: the stopping duty-cycle thread switched the heater off in its cleanup *after* the new state `1.0` had already been applied → heater off while status reported 100 %.)
- `CTL-045` `getHeatingStatus()` returns the last requested power `p` (0, 0.5, 1, …) — not the instantaneous relay state.
- `CTL-046` A simple **on/off** actuation strategy (any `p > 0` → on, status 1/0) existed in legacy as an alternative but was not used by the main application. It MAY be offered as configuration option `hardware.heating.mode = "onoff" | "dutycycle"` (default `dutycycle`).
