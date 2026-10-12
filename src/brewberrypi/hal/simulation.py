"""Simulation HAL for `--dummymode` (HW-060..064, NFR-051).

A simulated kettle: every simulated second the temperature rises by `heatingRatePerSecond · p` while heating
(up to `maxTemperature`) and falls by `coolingRatePerSecond` towards the ambient temperature while not.
The physics is computed from the clock whenever the state is read or changed, in whole seconds with the power
that was set during that second, so no background task is needed and a scaled or manual clock drives it
exactly. Pump and heating are kept in memory; there are no sensor errors.
"""

import logging
import threading

from brewberrypi.clock import Clock
from brewberrypi.config import SimulationConfig
from brewberrypi.hal import (
    LONG_BEEP,
    SHORT_BEEP,
    BeepPattern,
    Hal,
    Temperature,
    clamp_power,
    round_temperature,
)
from brewberrypi.hal.sound import Player, pattern_wav

log = logging.getLogger(__name__)

STEP_SECONDS = 1.0


class SimulationHal(Hal):
    def __init__(self, clock: Clock, config: SimulationConfig, player: Player | None = None) -> None:
        self._clock = clock
        self._config = config
        self._player = player
        self._lock = threading.Lock()
        self._temperature = config.start_temperature
        self._heating = 0.0
        self._pump = False
        self._last_step = clock.monotonic()
        log.info(
            "simulation: kettle at %.1f °C, time scale %s, beeps %s",
            self._temperature,
            config.time_scale,
            "on the audio output" if player is not None else "logged only",
        )

    # --- HW-001 operations ---

    def switch_on_pump(self) -> None:
        self._set_pump(True)

    def switch_off_pump(self) -> None:
        self._set_pump(False)

    def get_pump_status(self) -> bool:
        with self._lock:
            return self._pump

    def set_heating(self, power: float) -> None:
        with self._lock:
            self._simulate()
            self._change_heating(clamp_power(power))

    def get_heating_status(self) -> float:
        with self._lock:
            return self._heating

    def get_temperature(self) -> Temperature:
        with self._lock:
            self._simulate()
            return round_temperature(self._temperature)

    def short_beep(self) -> None:
        self._beep("short", SHORT_BEEP)

    def long_beep(self) -> None:
        self._beep("long", LONG_BEEP)

    def switch_everything_off(self) -> None:
        with self._lock:
            self._simulate()
            self._change_heating(0.0)
            self._change_pump(False)

    # --- internals ---

    def _set_pump(self, on: bool) -> None:
        with self._lock:
            self._change_pump(on)

    def _change_pump(self, on: bool) -> None:
        if on != self._pump:
            self._pump = on
            log.info("change pump status to %s", "on" if on else "off")  # HW-063

    def _change_heating(self, power: float) -> None:
        if power != self._heating:
            self._heating = power
            log.info("change heating status to %s", power)  # HW-063, NFR-041

    def _simulate(self) -> None:
        """Apply the physics for every whole simulated second since the last step (HW-060)."""
        config = self._config
        now = self._clock.monotonic()
        while now - self._last_step >= STEP_SECONDS:
            self._last_step += STEP_SECONDS
            if self._heating > 0:
                if self._temperature <= config.max_temperature:
                    self._temperature += config.heating_rate_per_second * self._heating
            elif self._temperature > config.ambient_temperature:
                self._temperature = max(
                    config.ambient_temperature, self._temperature - config.cooling_rate_per_second
                )

    def _beep(self, name: str, pattern: BeepPattern) -> None:
        log.info("beep: %s", name)
        if self._player is not None:
            self._player(pattern_wav(pattern))
