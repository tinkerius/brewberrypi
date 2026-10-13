"""M11: auxiliary tools (spec 12: TOOL-001..003)."""

import asyncio
import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from brewberrypi import tools
from brewberrypi.clock import ManualClock
from brewberrypi.hal.ds18b20 import SensorError
from brewberrypi.hal.mock import HalEvent, MockHal
from brewberrypi.hal.simulation import SimulationHal


def readings(*values: float | Exception) -> Callable[[], float]:
    queue = list(values)

    def read() -> float:
        value = queue.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    return read


def ticking(clock: ManualClock, start: datetime) -> Callable[[], datetime]:
    return lambda: start + timedelta(seconds=clock.monotonic())


START = datetime(2026, 10, 12, 13, 5, 9)


# --- TOOL-001 ---


def test_TOOL_001_line_format_24_hour_clock_and_error() -> None:
    assert tools.log_line(START, 62.46) == "2026/10/12 13:05:09;62.5"
    assert tools.log_line(START, 20) == "2026/10/12 13:05:09;20.0"
    assert tools.log_line(START, None) == "2026/10/12 13:05:09;ERROR"
    assert tools.log_line(datetime(2026, 1, 2, 3, 4, 5), -1.25) == "2026/01/02 03:04:05;-1.3"  # half-up


async def test_TOOL_001_logs_every_second_to_the_file_and_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clock = ManualClock()
    file = tmp_path / "temperatureLog.csv"
    file.write_text("existing line\n")  # appended, not replaced
    with file.open("a", encoding="utf-8") as output:
        logger = asyncio.create_task(
            tools.log_temperatures(
                readings(20.0, SensorError("CRC"), 20.1), output, clock, ticking(clock, START), count=3
            )
        )
        await clock.advance(0)
        assert file.read_text().endswith("2026/10/12 13:05:09;20.0\n")  # on disk at once
        await clock.advance(3)
        await logger
    assert file.read_text().splitlines() == [
        "existing line",
        "2026/10/12 13:05:09;20.0",
        "2026/10/12 13:05:10;ERROR",
        "2026/10/12 13:05:11;20.1",
    ]
    assert capsys.readouterr().out.splitlines() == file.read_text().splitlines()[1:]


async def test_fixed_schedule_is_not_shifted_by_slow_reads() -> None:
    clock = ManualClock()
    times: list[float] = []
    task = asyncio.create_task(tools.every(clock, 1.0, lambda: times.append(clock.monotonic()), count=4))
    await clock.advance(10)
    await task
    assert times == [0, 1, 2, 3]


def test_TOOL_001_command_line_with_dummymode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    original = tools.log_temperatures

    async def one_line(read: tools.Read, output, clock, now, count=None):  # type: ignore[no-untyped-def]
        await original(read, output, ManualClock(), now, count=1)

    monkeypatch.setattr(tools, "log_temperatures", one_line)
    assert tools.temperature_logger(["--dummymode"]) == 0
    [line] = (tmp_path / "temperatureLog.csv").read_text().splitlines()
    assert line.endswith(";20.0")


# --- TOOL-003 ---


async def test_TOOL_003_prints_readings_and_failures(capsys: pytest.CaptureFixture[str]) -> None:
    clock = ManualClock()
    read = readings(19.95, SensorError("no DS18B20 sensor (28-*) in /sys/bus/w1/devices"), 21.0)
    task = asyncio.create_task(tools.print_temperatures(read, clock, ticking(clock, START), count=3))
    await clock.advance(3)
    await task
    output = capsys.readouterr()
    assert output.out.splitlines() == ["2026/10/12 13:05:09;20.0", "2026/10/12 13:05:11;21.0"]
    assert output.err.splitlines() == [
        "Temperature could not be read: no DS18B20 sensor (28-*) in /sys/bus/w1/devices"
    ]


# --- TOOL-002 ---


async def test_TOOL_002_cycles_the_outputs_every_2_s(capsys: pytest.CaptureFixture[str]) -> None:
    clock = ManualClock()
    hal = MockHal(clock)
    task = asyncio.create_task(tools.cycle_outputs(hal, {"heating": 23, "pump": 22}, clock, rounds=1))
    await clock.advance(10)
    await task
    assert hal.events == [
        HalEvent(2, "heating", 1.0),
        HalEvent(4, "heating", 0.0),
        HalEvent(6, "pump", True),
        HalEvent(8, "pump", False),
        HalEvent(10, "short_beep"),
    ]
    assert capsys.readouterr().out.splitlines() == [
        "heating (BCM 23): on",
        "heating (BCM 23): off",
        "pump (BCM 22): on",
        "pump (BCM 22): off",
        "buzzer pulse for 500ms",
    ]


async def test_TOOL_002_duty_cycle_mode() -> None:
    clock = ManualClock()
    hal = MockHal(clock)
    task = asyncio.create_task(tools.cycle_duty(hal, clock, 10000, rounds=1))
    await clock.advance(1000)
    await task
    powers = [(round(e.time, 3), e.value) for e in hal.events if e.operation == "heating"]
    # each power for two periods of its duty cycle (CTL-042), at least 20 s
    steps = [20, 200, 100, 66.666, 50, 40, 50, 66.666, 100, 200]
    starts = [round(sum(steps[:i]), 3) for i in range(11)]
    assert powers == [(starts[i], i / 10) for i in range(11)]
    assert starts[-1] + 20 < 16 * 60  # one round takes about 15 minutes


def test_TOOL_002_switches_everything_off_on_exit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    closed: list[bool] = []

    async def interrupted(hal, pins, clock, rounds=None):  # type: ignore[no-untyped-def]
        hal.set_heating(1.0)
        raise KeyboardInterrupt  # Ctrl+C

    original_close = SimulationHal.close

    async def close(self: SimulationHal) -> None:
        await original_close(self)
        closed.append(self.get_heating_status() == 0.0 and not self.get_pump_status())

    monkeypatch.setattr(tools, "cycle_outputs", interrupted)
    monkeypatch.setattr(SimulationHal, "close", close)
    assert tools.gpio_test(["--dummymode"]) == 0
    assert closed == [True]
    assert "all outputs off" in capsys.readouterr().out


def test_TOOL_002_without_gpio_is_a_hardware_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert tools.gpio_test([]) == tools.EXIT_HARDWARE  # no libgpiod bindings or chip here
    assert "hardware initialisation failed" in capsys.readouterr().err


def test_tools_use_the_application_configuration(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"hardware": {"heating": {"pin": 99}}}))
    assert tools.sensor_test(["--config", str(tmp_path / "config.json")]) == tools.EXIT_INVALID_CONFIG
    assert "hardware.heating.pin must be smaller than or equal to 27" in capsys.readouterr().err
