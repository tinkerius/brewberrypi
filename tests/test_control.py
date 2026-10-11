"""M3: temperature controller, temperature progress, countdown (spec 05, AC-001..007).

These tests cover the controller part of each criterion. The goal-level parts (goal Done, goal status) follow
with the goals in M4, `/hardware/status` in M7 and the UI in M8.
"""

import logging
from pathlib import Path

import pytest

from brewberrypi.clock import ManualClock
from brewberrypi.config import ControlConfig, load_config
from brewberrypi.control import Countdown, Progress, RunningTime, TemperatureController, temperature_progress
from brewberrypi.hal.mock import MockHal

EXAMPLE_CONFIG = Path(__file__).parents[1] / "docs" / "specification" / "data" / "config.example.json"
DEFAULTS = load_config(EXAMPLE_CONFIG).control


def controller(
    temperature: float | None = 20.0, heating: float = 0.0
) -> tuple[MockHal, TemperatureController]:
    hal = MockHal(temperature=temperature)
    hal.set_heating(heating)
    return hal, TemperatureController(hal, DEFAULTS)


# --- holdTemperature (CTL-010..014) ---


def test_AC_001_heater_off_stays_off_until_below_the_lower_switch_point() -> None:
    hal, control = controller(temperature=61.95, heating=0.0)
    assert control.hold(62.0) is False
    assert hal.get_heating_status() == 0.0  # switch point 61.9
    hal.set_temperature(61.85)
    control.hold(62.0)
    assert hal.get_heating_status() == 0.5


def test_AC_002_heater_on_stays_on_until_the_target_is_reached() -> None:
    hal, control = controller(temperature=61.95, heating=0.5)
    assert control.hold(62.0) is False
    assert hal.get_heating_status() == 0.5
    hal.set_temperature(62.0)
    assert control.hold(62.0) is True
    assert hal.get_heating_status() == 0.0


def test_AC_003_full_power_from_exactly_3_kelvin_below_the_target() -> None:
    hal, control = controller(temperature=59.0, heating=0.0)
    control.hold(62.0)
    assert hal.get_heating_status() == 1.0
    hal.set_temperature(59.1)
    control.hold(62.0)
    assert hal.get_heating_status() == 0.5


def test_AC_004_boost_heats_at_full_power_and_stays_on_when_reached() -> None:
    hal, control = controller(temperature=96.9, heating=0.0)
    assert control.hold(97.0, boost=True) is False
    assert hal.get_heating_status() == 1.0
    hal.set_temperature(97.0)
    assert control.hold(97.0, boost=True) is True
    assert hal.get_heating_status() == 1.0


def test_AC_005_invalid_reading_switches_the_heater_off_and_control_resumes() -> None:
    hal, control = controller(temperature=20.0, heating=1.0)
    control.hold(62.0)
    hal.set_temperature(41.0)
    control.hold(62.0)
    assert hal.get_heating_status() == 1.0
    assert control.progress == Progress(50, "50%")

    hal.set_temperature(None)
    assert control.hold(62.0) is False
    assert hal.get_heating_status() == 0.0
    assert control.progress == Progress(50, "Sensor error")  # percent unchanged

    hal.set_temperature(41.0)
    control.hold(62.0)
    assert hal.get_heating_status() == 1.0
    assert control.progress == Progress(50, "50%")


def test_invalid_first_reading_does_not_capture_a_start_temperature() -> None:
    hal, control = controller(temperature=None)
    control.hold(62.0)
    assert control.start_temperature is None
    assert control.progress == Progress(0, "Sensor error")
    hal.set_temperature(30.0)
    control.hold(62.0)
    assert control.start_temperature == 30.0


def test_CTL_010_pump_is_switched_on_on_every_call() -> None:
    hal, control = controller(temperature=None)
    control.hold(62.0)
    assert hal.get_pump_status() is True
    hal.switch_off_pump()
    hal.set_temperature(70.0)
    control.hold(62.0)
    assert hal.get_pump_status() is True


def test_CTL_014_no_active_cooling_above_the_target() -> None:
    hal, control = controller(temperature=70.0, heating=1.0)
    assert control.hold(62.0) is True
    assert hal.get_heating_status() == 0.0


def test_CTL_011_hysteresis_cycle() -> None:
    hal, control = controller(temperature=55.0)
    steps = [(55.0, 1.0), (59.5, 0.5), (61.9, 0.5), (62.0, 0.0), (61.9, 0.0), (61.8, 0.5), (62.1, 0.0)]
    for temperature, expected in steps:
        hal.set_temperature(temperature)
        control.hold(62.0)
        assert hal.get_heating_status() == expected, temperature


def test_hysteresis_and_band_come_from_the_configuration() -> None:
    hal = MockHal(temperature=60.5)
    config = ControlConfig(
        hysteresis_upper_offset=0.5, hysteresis_lower_offset=-1.0, near_target_band=1.0, near_target_power=0.3
    )
    control = TemperatureController(hal, config)
    control.hold(62.0)
    assert hal.get_heating_status() == 1.0  # 1.5 K below: outside the 1 K band
    hal.set_temperature(62.2)
    control.hold(62.0)
    assert hal.get_heating_status() == 0.3  # heater on: switch point 62.5
    hal.set_temperature(62.6)
    control.hold(62.0)
    assert hal.get_heating_status() == 0.0
    hal.set_temperature(61.5)
    control.hold(62.0)
    assert hal.get_heating_status() == 0.0  # heater off: switch point 61.0


def test_CTL_015_every_call_logs_the_decision_at_debug_level(caplog: pytest.LogCaptureFixture) -> None:
    _, control = controller(temperature=61.85)
    with caplog.at_level(logging.DEBUG, logger="brewberrypi.control"):
        control.hold(62.0)
    assert caplog.messages == ["target 62.0, temperature 61.9, switch point 61.90: heating 0.5"]


# --- temperature progress (CTL-020) ---


def test_AC_006_temperature_progress() -> None:
    assert temperature_progress(start=20.0, target=62.0, current=41.0) == Progress(50, "50%")


def test_AC_006_start_above_the_target_is_done_on_the_first_tick() -> None:
    hal, control = controller(temperature=62.5)
    assert control.hold(62.0) is True
    assert control.progress == Progress(100, "100%")
    assert hal.get_heating_status() == 0.0


@pytest.mark.parametrize(
    ("start", "target", "current", "percent"),
    [
        (20.0, 62.0, 20.0, 0),
        (20.0, 62.0, 61.9, 99),
        (20.0, 62.0, 62.0, 100),
        (20.0, 62.0, 70.0, 100),  # clamped
        (20.0, 62.0, 18.0, 0),  # clamped
        (62.0, 62.0, 61.9, 0),  # start == target: no division by zero
        (62.0, 62.0, 62.0, 100),
        (15.0, 50.0, 16.4, 4),  # exactly 4 %; binary floating point gives 3.9999... -> 3
        (15.0, 50.0, 22.7, 22),  # exactly 22 %; floating point gives 21
    ],
)
def test_CTL_020_progress_is_truncated_and_clamped(
    start: float, target: float, current: float, percent: int
) -> None:
    assert temperature_progress(start, target, current) == Progress(percent, f"{percent}%")


# --- countdown (CTL-030, CTL-031) and running time (ENG-030, ENG-031) ---


async def test_AC_007_rest_countdown_progress() -> None:
    clock = ManualClock()
    countdown = Countdown(10, clock.monotonic)
    assert countdown.elapsed() is False
    assert countdown.progress == Progress(0, "10:00 left")
    await clock.advance(4 * 60)
    assert countdown.elapsed() is False
    assert countdown.progress == Progress(40, "06:00 left")
    await clock.advance(6 * 60)
    assert countdown.elapsed() is True
    assert countdown.progress == Progress(100, "00:00 left")
    await clock.advance(5 * 60)
    assert countdown.elapsed() is True
    assert countdown.progress == Progress(100, "00:00 left")  # never negative


async def test_CTL_030_countdown_starts_on_the_first_call() -> None:
    clock = ManualClock()
    countdown = Countdown(1, clock.monotonic)
    await clock.advance(120)
    assert countdown.progress == Progress(0, "01:00 left")
    assert countdown.elapsed() is False
    await clock.advance(59.5)
    assert countdown.progress == Progress(99, "00:00 left")
    assert countdown.elapsed() is False
    await clock.advance(0.5)
    assert countdown.elapsed() is True


def test_CTL_030_zero_minutes_elapse_immediately() -> None:
    countdown = Countdown(0, ManualClock().monotonic)
    assert countdown.elapsed() is True
    assert countdown.progress == Progress(100, "00:00 left")


def test_CTL_031_long_rest_shows_minutes_above_99() -> None:
    countdown = Countdown(110, ManualClock().monotonic)
    countdown.elapsed()
    assert countdown.progress == Progress(0, "110:00 left")


async def test_countdown_reset_starts_afresh() -> None:
    clock = ManualClock()
    countdown = Countdown(1, clock.monotonic)
    countdown.elapsed()
    await clock.advance(60)
    assert countdown.elapsed() is True
    countdown.reset()
    await clock.advance(30)
    assert countdown.elapsed() is False
    assert countdown.progress == Progress(0, "01:00 left")


async def test_ENG_031_countdown_freezes_while_paused() -> None:
    clock = ManualClock()
    running = RunningTime(clock)
    countdown = Countdown(10, running)
    countdown.elapsed()
    await clock.advance(4 * 60)
    running.pause()
    assert running.paused
    await clock.advance(30 * 60)
    assert countdown.progress == Progress(40, "06:00 left")
    running.resume()
    assert not running.paused
    await clock.advance(6 * 60)
    assert countdown.elapsed() is True


async def test_running_time_pause_and_resume_are_idempotent() -> None:
    clock = ManualClock(start=100)
    running = RunningTime(clock)
    running.resume()
    await clock.advance(10)
    running.pause()
    running.pause()
    await clock.advance(10)
    running.resume()
    running.resume()
    await clock.advance(1)
    assert running() == 111  # 121 s on the clock minus 10 s paused
