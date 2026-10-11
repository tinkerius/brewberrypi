"""Mock HAL for unit tests (NFR-060).

The test sets the temperature with `set_temperature()` and checks the outputs, either as current state
(`get_pump_status()`, `get_heating_status()`) or as the recorded history in `events`, timestamped with the
monotonic time of the clock passed in (typically a `ManualClock`).
"""

import threading
from dataclasses import dataclass
from typing import Literal

from brewberrypi.clock import Clock, ManualClock
from brewberrypi.hal import Hal, Temperature, clamp_power

Operation = Literal["pump", "heating", "short_beep", "long_beep", "switch_everything_off"]


@dataclass(frozen=True)
class HalEvent:
    time: float
    """`clock.monotonic()` when the operation was called."""
    operation: Operation
    value: bool | float | None = None
    """New pump status for `pump`, clamped power for `heating`, else `None`."""


class MockHal(Hal):
    """In-memory HAL. Starts with every output off (HW-020) and an INVALID temperature until set."""

    def __init__(self, clock: Clock | None = None, temperature: Temperature = None) -> None:
        self._clock = clock if clock is not None else ManualClock()
        self._lock = threading.Lock()
        self._pump = False
        self._heating = 0.0
        self._temperature = temperature
        self._events: list[HalEvent] = []

    # --- HW-001 operations ---

    def switch_on_pump(self) -> None:
        with self._lock:
            self._pump = True
            self._record("pump", True)

    def switch_off_pump(self) -> None:
        with self._lock:
            self._pump = False
            self._record("pump", False)

    def get_pump_status(self) -> bool:
        with self._lock:
            return self._pump

    def set_heating(self, power: float) -> None:
        with self._lock:
            self._heating = clamp_power(power)
            self._record("heating", self._heating)

    def get_heating_status(self) -> float:
        with self._lock:
            return self._heating

    def get_temperature(self) -> Temperature:
        with self._lock:
            return self._temperature

    def short_beep(self) -> None:
        with self._lock:
            self._record("short_beep")

    def long_beep(self) -> None:
        with self._lock:
            self._record("long_beep")

    def switch_everything_off(self) -> None:
        with self._lock:
            self._heating = 0.0
            self._pump = False
            self._record("switch_everything_off")

    # --- Test control ---

    def set_temperature(self, temperature: Temperature) -> None:
        """The value `get_temperature()` returns from now on; `None` simulates an INVALID reading."""
        with self._lock:
            self._temperature = temperature

    @property
    def events(self) -> list[HalEvent]:
        """Copy of all recorded operations, oldest first."""
        with self._lock:
            return list(self._events)

    def beeps(self) -> list[Operation]:
        """The beeps played so far (`short_beep`, `long_beep`), in order."""
        with self._lock:
            return [e.operation for e in self._events if e.operation in ("short_beep", "long_beep")]

    def clear_events(self) -> None:
        with self._lock:
            self._events.clear()

    def _record(self, operation: Operation, value: bool | float | None = None) -> None:
        self._events.append(HalEvent(self._clock.monotonic(), operation, value))
