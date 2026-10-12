"""Auxiliary command-line tools for installation and diagnosis on the Raspberry Pi (spec 12).

They use the main application's configuration file and HAL code (legacy tools had their own copies of pin
numbers and sensor code):

- `brewberrypi-temperature-logger` (TOOL-001): appends the temperature to a CSV file every second.
- `brewberrypi-gpio-test` (TOOL-002): switches the outputs in a cycle so the wiring can be checked.
- `brewberrypi-sensor-test` (TOOL-003): prints the DS18B20 temperature about once per second.

The logger and the sensor test read the sensor directly and request no GPIO lines, so they never switch an
output and can run while the main application is running. All tools accept `--config` and `--dummymode`.
"""

import argparse
import asyncio
import contextlib
import logging
import os
import sys
from collections.abc import Callable, Coroutine, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from brewberrypi.clock import Clock, SystemClock
from brewberrypi.config import Config, ConfigError, load_config
from brewberrypi.hal import Hal, round_temperature
from brewberrypi.hal.ds18b20 import SensorError, read_sensor
from brewberrypi.hal.gpio import GpioError
from brewberrypi.hal.raspberry_pi import RaspberryPiHal
from brewberrypi.hal.simulation import SimulationHal

EXIT_OK = 0
EXIT_INVALID_CONFIG = 2
EXIT_HARDWARE = 4

DEFAULT_LOG_FILE = "temperatureLog.csv"
READ_PERIOD_SECONDS = 1.0
GPIO_STEP_SECONDS = 2.0
DUTY_STEP_SECONDS = 10.0

Read = Callable[[], float]
"""One temperature reading; raises `SensorError` when there is none."""


def timestamp(moment: datetime) -> str:
    """`yyyy/MM/dd HH:mm:ss`, 24-hour clock (FIX-19)."""
    return moment.strftime("%Y/%m/%d %H:%M:%S")


def log_line(moment: datetime, temperature: float | None) -> str:
    """TOOL-001: `<timestamp>;<temperature>` with one decimal and `.`, or `ERROR` for INVALID."""
    return f"{timestamp(moment)};{'ERROR' if temperature is None else degrees(temperature)}"


def degrees(temperature: float) -> str:
    """One decimal with `.`, rounded half-up like the sensor (HW-031)."""
    return f"{round_temperature(temperature):.1f}"


async def every(clock: Clock, period: float, step: Callable[[], object], count: int | None = None) -> None:
    """Run `step` every `period` seconds on a fixed schedule (a slow step does not shift later ones)."""
    start = clock.monotonic()
    done = 0
    while True:
        step()
        done += 1
        if count is not None and done >= count:
            return
        await clock.sleep(max(0.0, start + done * period - clock.monotonic()))


async def log_temperatures(
    read: Read, output: TextIO, clock: Clock, now: Callable[[], datetime], count: int | None = None
) -> None:
    """TOOL-001: one line per second to the file and to stdout; every line is on disk at once."""

    def step() -> None:
        try:
            temperature: float | None = read()
        except SensorError:
            temperature = None
        line = log_line(now(), temperature)
        output.write(line + "\n")
        output.flush()
        os.fsync(output.fileno())  # safe against power loss
        print(line, flush=True)

    await every(clock, READ_PERIOD_SECONDS, step, count)


async def print_temperatures(
    read: Read, clock: Clock, now: Callable[[], datetime], count: int | None = None
) -> None:
    """TOOL-003: `<timestamp>;<temperature>` on stdout at about 1 Hz, the reason of failures on stderr."""

    def step() -> None:
        try:
            temperature = read()
        except SensorError as error:
            print(f"Temperature could not be read: {error}", file=sys.stderr, flush=True)
        else:
            print(f"{timestamp(now())};{degrees(temperature)}", flush=True)

    await every(clock, READ_PERIOD_SECONDS, step, count)


async def cycle_outputs(hal: Hal, pins: dict[str, int], clock: Clock, rounds: int | None = None) -> None:
    """TOOL-002: heating on/off, pump on/off, buzzer pulse, each after 2 s, printing pin and state."""
    steps: list[tuple[Callable[[], None], str]] = [
        (lambda: hal.set_heating(1.0), f"heating (BCM {pins['heating']}): on"),
        (lambda: hal.set_heating(0.0), f"heating (BCM {pins['heating']}): off"),
        (hal.switch_on_pump, f"pump (BCM {pins['pump']}): on"),
        (hal.switch_off_pump, f"pump (BCM {pins['pump']}): off"),
        (hal.short_beep, "buzzer pulse for 500ms"),
    ]
    done = 0
    while rounds is None or done < rounds:
        for action, message in steps:
            await clock.sleep(GPIO_STEP_SECONDS)
            action()
            print(message, flush=True)
        done += 1


async def cycle_duty(hal: Hal, clock: Clock, rounds: int | None = None) -> None:
    """TOOL-002 optional mode: heating power 0.0, 0.1 … 1.0, each for 10 s, to check CTL-042."""
    done = 0
    while rounds is None or done < rounds:
        for tenth in range(11):
            hal.set_heating(tenth / 10)
            print(f"heating power {tenth / 10:.1f}", flush=True)
            await clock.sleep(DUTY_STEP_SECONDS)
        done += 1


# --- command lines ---


def _parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", metavar="PATH", type=Path, help="configuration file (as for brewberrypi)")
    parser.add_argument("--dummymode", action="store_true", help="simulation instead of the Raspberry Pi")
    return parser


def _setup(args: argparse.Namespace) -> Config | None:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        return load_config(args.config)
    except ConfigError as error:
        print(f"invalid configuration: {error}", file=sys.stderr)
        return None


def _reader(config: Config, dummymode: bool) -> Read:
    if dummymode:
        simulation = SimulationHal(SystemClock(), config.simulation)

        def simulated() -> float:
            temperature = simulation.get_temperature()
            if temperature is None:
                raise SensorError("no simulated reading")
            return temperature

        return simulated
    sensor = config.hardware.sensor
    return lambda: read_sensor(sensor.devices_path, sensor.sensor_id)


def _run(main: Callable[[], Coroutine[Any, Any, None]]) -> int:
    """Run until Ctrl+C; cleanup in the coroutine's `finally` still runs."""
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
    return EXIT_OK


def temperature_logger(argv: Sequence[str] | None = None) -> int:
    """`brewberrypi-temperature-logger [FILE]` (TOOL-001)."""
    parser = _parser("Append the kettle temperature to a CSV file every second (TOOL-001).")
    parser.add_argument(
        "file", nargs="?", type=Path, default=Path(DEFAULT_LOG_FILE), help="default: %(default)s"
    )
    args = parser.parse_args(argv)
    config = _setup(args)
    if config is None:
        return EXIT_INVALID_CONFIG
    read = _reader(config, args.dummymode)
    with args.file.open("a", encoding="utf-8") as output:
        return _run(lambda: log_temperatures(read, output, SystemClock(), datetime.now))


def sensor_test(argv: Sequence[str] | None = None) -> int:
    """`brewberrypi-sensor-test` (TOOL-003)."""
    args = _parser("Print the DS18B20 temperature about once per second (TOOL-003).").parse_args(argv)
    config = _setup(args)
    if config is None:
        return EXIT_INVALID_CONFIG
    read = _reader(config, args.dummymode)
    return _run(lambda: print_temperatures(read, SystemClock(), datetime.now))


def gpio_test(argv: Sequence[str] | None = None) -> int:
    """`brewberrypi-gpio-test [--duty-cycle]` (TOOL-002)."""
    parser = _parser("Switch the outputs in a cycle to check the wiring (TOOL-002).")
    parser.add_argument(
        "--duty-cycle", action="store_true", help="cycle the heating power 0.0..1.0 every 10 s"
    )
    args = parser.parse_args(argv)
    config = _setup(args)
    if config is None:
        return EXIT_INVALID_CONFIG
    clock = SystemClock()
    hardware = config.hardware
    try:
        hal: Hal = (
            SimulationHal(clock, config.simulation) if args.dummymode else RaspberryPiHal(clock, hardware)
        )
    except GpioError as error:
        print(f"hardware initialisation failed: {error}", file=sys.stderr)
        return EXIT_HARDWARE
    pins = {"heating": hardware.heating.pin, "pump": hardware.pump.pin}

    async def main() -> None:
        try:
            await (cycle_duty(hal, clock) if args.duty_cycle else cycle_outputs(hal, pins, clock))
        finally:
            await hal.close()  # heating, pump and buzzer off, GPIO released
            print("all outputs off", flush=True)

    return _run(main)
