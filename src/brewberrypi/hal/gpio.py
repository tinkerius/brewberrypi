"""GPIO outputs through libgpiod v2 (ADR-0001, HW-010..012, HW-020).

The header GPIO chip is found by its label, because chip numbers change between kernels and Raspberry Pi
models. All output lines are requested in their off state at once, with a bias towards off, so the relays
are off before anything else happens (HW-020, NFR-002). Active-low relays are handled by libgpiod's
`active_low` line setting: callers only say "on" or "off".
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

log = logging.getLogger(__name__)

CHIP_LABELS = ("pinctrl-bcm2835", "pinctrl-bcm2711", "pinctrl-rp1")
"""Header GPIO chips of the Raspberry Pi 3, 4 and 5 (Q-25: not configurable yet)."""

CONSUMER = "brewberrypi"


class GpioError(Exception):
    """GPIO initialisation failed (startup exit code 4)."""


@dataclass(frozen=True)
class Output:
    pin: int
    """BCM GPIO number."""
    active_low: bool


class Outputs(Protocol):
    """The relay and buzzer outputs."""

    def set(self, pin: int, on: bool) -> None: ...

    def close(self) -> None:
        """Release the lines (HW-021)."""
        ...


class LibgpiodOutputs:
    """Outputs on the Raspberry Pi header chip."""

    def __init__(
        self, outputs: Iterable[Output], gpiod: ModuleType | None = None, dev: Path = Path("/dev")
    ) -> None:
        if gpiod is None:
            try:
                import gpiod as gpiod_module  # noqa: PLC0415  (only on the device; python3-libgpiod)
            except ImportError as error:
                raise GpioError(
                    "the libgpiod Python bindings (python3-libgpiod) are not installed"
                ) from error
            gpiod = gpiod_module
        self._gpiod = gpiod
        from_line = gpiod.line
        path = find_chip(gpiod, dev)
        config = {
            output.pin: gpiod.LineSettings(
                direction=from_line.Direction.OUTPUT,
                active_low=output.active_low,
                output_value=from_line.Value.INACTIVE,  # off before anything else (HW-020)
                bias=from_line.Bias.PULL_UP if output.active_low else from_line.Bias.PULL_DOWN,
            )
            for output in outputs
        }
        try:
            with gpiod.Chip(str(path)) as chip:
                self._request: Any = chip.request_lines(consumer=CONSUMER, config=config)
        except OSError as error:
            raise GpioError(f"cannot request GPIO lines {sorted(config)} on {path}: {error}") from error
        log.info("GPIO lines %s requested on %s, all off", sorted(config), path)

    def set(self, pin: int, on: bool) -> None:
        value = self._gpiod.line.Value
        self._request.set_value(pin, value.ACTIVE if on else value.INACTIVE)

    def close(self) -> None:
        self._request.release()
        log.info("GPIO lines released")


def find_chip(gpiod: ModuleType, dev: Path = Path("/dev")) -> Path:
    """The `/dev/gpiochip*` whose label is one of `CHIP_LABELS`."""
    for path in sorted(dev.glob("gpiochip*")):
        try:
            with gpiod.Chip(str(path)) as chip:
                label: str = chip.get_info().label
        except OSError:
            continue
        if label in CHIP_LABELS:
            return path
    raise GpioError(f"no GPIO chip with a label of {', '.join(CHIP_LABELS)} in {dev}")
