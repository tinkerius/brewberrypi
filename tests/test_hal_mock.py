"""M2: HAL interface and mock HAL (HW-001..003, HW-020, NFR-060)."""

import asyncio
import math
import threading

import pytest

from brewberrypi.clock import Clock, ManualClock
from brewberrypi.hal import Hal, clamp_power
from brewberrypi.hal.mock import HalEvent, MockHal

HW_001_OPERATIONS = {
    "switch_on_pump",
    "switch_off_pump",
    "get_pump_status",
    "set_heating",
    "get_heating_status",
    "get_temperature",
    "short_beep",
    "long_beep",
    "switch_everything_off",
}


def test_HW_001_interface_has_exactly_the_specified_operations() -> None:
    assert Hal.__abstractmethods__ == HW_001_OPERATIONS


def test_HW_020_mock_starts_with_everything_off_and_invalid_temperature() -> None:
    hal = MockHal()
    assert hal.get_pump_status() is False
    assert hal.get_heating_status() == 0.0
    assert hal.get_temperature() is None
    assert hal.events == []


def test_pump_switching_is_idempotent() -> None:
    hal = MockHal()
    hal.switch_on_pump()
    hal.switch_on_pump()
    assert hal.get_pump_status() is True
    hal.switch_off_pump()
    hal.switch_off_pump()
    assert hal.get_pump_status() is False


@pytest.mark.parametrize(
    ("requested", "stored"),
    [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (1.7, 1.0), (-0.3, 0.0), (math.nan, 0.0), (-math.inf, 0.0)],
)
def test_HW_001_heating_power_is_clamped(requested: float, stored: float) -> None:
    hal = MockHal()
    hal.set_heating(requested)
    assert hal.get_heating_status() == stored
    assert clamp_power(requested) == stored


def test_switch_everything_off() -> None:
    hal = MockHal()
    hal.switch_on_pump()
    hal.set_heating(0.8)
    hal.switch_everything_off()
    assert hal.get_pump_status() is False
    assert hal.get_heating_status() == 0.0


def test_test_controls_the_temperature_including_invalid() -> None:
    hal = MockHal(temperature=20.0)
    assert hal.get_temperature() == 20.0
    hal.set_temperature(62.4)
    assert hal.get_temperature() == 62.4
    hal.set_temperature(None)
    assert hal.get_temperature() is None


async def test_events_are_recorded_with_the_clock_time() -> None:
    clock = ManualClock()
    hal = MockHal(clock)
    hal.switch_on_pump()
    await clock.advance(1.5)
    hal.set_heating(2)
    hal.short_beep()
    await clock.advance(1)
    hal.long_beep()
    hal.switch_everything_off()
    assert hal.events == [
        HalEvent(0.0, "pump", True),
        HalEvent(1.5, "heating", 1.0),
        HalEvent(1.5, "short_beep"),
        HalEvent(2.5, "long_beep"),
        HalEvent(2.5, "switch_everything_off"),
    ]
    assert hal.beeps() == ["short_beep", "long_beep"]
    hal.clear_events()
    assert hal.events == []


def test_HW_003_operations_are_thread_safe() -> None:
    hal = MockHal()
    rounds = 2000

    def worker(power: float) -> None:
        for _ in range(rounds):
            hal.set_heating(power)
            hal.switch_on_pump()
            assert hal.get_heating_status() in (0.25, 0.75)
            hal.switch_off_pump()

    threads = [threading.Thread(target=worker, args=(p,)) for p in (0.25, 0.75) * 4]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(hal.events) == len(threads) * rounds * 3


async def test_NFR_060_unit_tests_drive_time_and_temperature() -> None:
    """M2 done criterion: a loop against the mock HAL runs on test-controlled time and temperature."""
    clock = ManualClock()
    hal = MockHal(clock, temperature=20.0)

    async def thermostat(hal: Hal, clock: Clock, target: float) -> None:
        while True:
            temperature = hal.get_temperature()
            hal.set_heating(1.0 if temperature is not None and temperature < target else 0.0)
            await clock.sleep(0.5)

    task = asyncio.create_task(thermostat(hal, clock, target=62.0))
    await clock.advance(0)
    assert hal.get_heating_status() == 1.0

    await clock.advance(30 * 60)  # half an hour without a real sleep
    hal.set_temperature(62.0)
    await clock.advance(0.5)
    assert hal.get_heating_status() == 0.0

    hal.set_temperature(None)  # INVALID reading: heater stays off (HW-022)
    await clock.advance(0.5)
    assert hal.get_heating_status() == 0.0

    heating_events = [e for e in hal.events if e.operation == "heating"]
    assert len(heating_events) == 30 * 60 * 2 + 3
    assert heating_events[-1].time == 30 * 60 + 1.0
    task.cancel()
