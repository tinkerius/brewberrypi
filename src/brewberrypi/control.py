"""Temperature control building blocks for the goals (spec 05: CTL-010..031, ENG-030/031).

- `TemperatureController.hold()`: the hysteresis controller `holdTemperature(T, boost)` with temperature
  progress, one instance per goal instance.
- `Countdown`: `countdown(M)` with time progress, counting running time only.
- `RunningTime`: a time source that stands still while the process is paused.

The duty cycle that turns a heating power into relay switching (CTL-040..046) lives in the HAL.
"""

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from brewberrypi.clock import Clock
from brewberrypi.config import ControlConfig
from brewberrypi.hal import Hal

log = logging.getLogger(__name__)

FULL_POWER = 1.0
SENSOR_ERROR = "Sensor error"


@dataclass(frozen=True)
class Progress:
    """A goal's `statusPercent` (0..100) and `statusMessage` (DOM-020)."""

    percent: int
    message: str


def _clamp_percent(percent: int) -> int:
    return max(0, min(100, percent))


def temperature_progress(start: float, target: float, current: float) -> Progress:
    """CTL-020, with FIX-14 for a start at or above the target.

    Computed on the decimal values as written (`62.0`, `41.0`), so `(total - remaining) * 100 / total` is
    exact and truncation never turns 50 % into 49 % through binary rounding.
    """
    start_d, target_d, current_d = (Decimal(repr(value)) for value in (start, target, current))
    total = target_d - start_d
    if total <= 0:
        percent = 100 if current_d >= target_d else 0
    else:
        remaining = target_d - current_d
        percent = _clamp_percent(math.trunc((total - remaining) * 100 / total))
    return Progress(percent, f"{percent}%")


class TemperatureController:
    """`holdTemperature(T, boost)` (CTL-010..015) and temperature progress (CTL-020) for one goal instance."""

    def __init__(self, hal: Hal, config: ControlConfig) -> None:
        self._hal = hal
        self._config = config
        self.start_temperature: float | None = None
        """The first valid reading of this goal instance."""
        self.progress = Progress(0, "0%")

    def hold(self, target: float, boost: bool = False) -> bool:
        """One control step; returns `True` when the current temperature has reached `target`."""
        hal = self._hal
        hal.switch_on_pump()
        current = hal.get_temperature()
        if current is None:  # FIX-02: no valid reading, heater off
            hal.set_heating(0)
            self.progress = Progress(self.progress.percent, SENSOR_ERROR)
            log.debug("target %.1f, temperature INVALID: heater off", target)
            return False
        if self.start_temperature is None:
            self.start_temperature = current
        self.progress = temperature_progress(self.start_temperature, target, current)

        if boost:
            power = FULL_POWER
            switch_point = None
        else:
            heater_on = hal.get_heating_status() > 0
            offset = (
                self._config.hysteresis_upper_offset if heater_on else self._config.hysteresis_lower_offset
            )
            switch_point = target + offset
            if current < switch_point:
                near = target - current < self._config.near_target_band
                power = self._config.near_target_power if near else FULL_POWER
            else:
                power = 0.0
        hal.set_heating(power)
        log.debug(
            "target %.1f, temperature %.1f, switch point %s: heating %s",
            target,
            current,
            "boost" if switch_point is None else f"{switch_point:.2f}",
            power,
        )
        return current >= target


class RunningTime:
    """Seconds of running time: a monotonic clock that stands still while paused (ENG-030, ENG-031)."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._paused_total = 0.0
        self._paused_since: float | None = None

    def __call__(self) -> float:
        now = self._clock.monotonic() if self._paused_since is None else self._paused_since
        return now - self._paused_total

    @property
    def paused(self) -> bool:
        return self._paused_since is not None

    def pause(self) -> None:
        if self._paused_since is None:
            self._paused_since = self._clock.monotonic()

    def resume(self) -> None:
        if self._paused_since is not None:
            self._paused_total += self._clock.monotonic() - self._paused_since
            self._paused_since = None


class Countdown:
    """`countdown(M)` (CTL-030) with time progress (CTL-031).

    `now` returns seconds of running time, normally a `RunningTime`, so the countdown freezes during a pause.
    """

    def __init__(self, minutes: int, now: Callable[[], float]) -> None:
        self._duration_ms = minutes * 60_000
        self._now = now
        self._started_at: float | None = None

    def elapsed(self) -> bool:
        """Starts the countdown on the first call; `True` once the time is up."""
        if self._started_at is None:
            self._started_at = self._now()
        return self.remaining_ms <= 0

    def reset(self) -> None:
        """The next `elapsed()` starts the countdown afresh (iodine test, GOAL-005)."""
        self._started_at = None

    @property
    def remaining_ms(self) -> int:
        if self._started_at is None:
            return self._duration_ms
        return self._duration_ms - round((self._now() - self._started_at) * 1000)

    @property
    def progress(self) -> Progress:
        remaining = self.remaining_ms
        if self._duration_ms > 0:
            percent = _clamp_percent((self._duration_ms - remaining) * 100 // self._duration_ms)
        else:
            percent = 100
        shown = max(remaining, 0)
        return Progress(percent, f"{shown // 60_000:02d}:{shown // 1000 % 60:02d} left")
