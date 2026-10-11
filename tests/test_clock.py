"""M2: controllable clock (NFR-005, NFR-060)."""

import asyncio
import time

import pytest

from brewberrypi.clock import Clock, ManualClock, SystemClock


async def test_manual_clock_only_moves_when_advanced() -> None:
    clock = ManualClock(start=100.0)
    assert clock.monotonic() == 100.0
    await clock.advance(2.5)
    assert clock.monotonic() == 102.5


async def test_wall_time_moves_with_the_monotonic_time() -> None:
    clock = ManualClock(start=0.0, wall_start=1_000.0)
    await clock.advance(60)
    assert clock.wall_time() == 1_060.0


async def test_sleep_returns_when_the_time_is_reached() -> None:
    clock = ManualClock()
    task = asyncio.create_task(clock.sleep(10))
    await clock.advance(9.9)
    assert not task.done()
    await clock.advance(0.1)
    assert task.done()


async def test_sleepers_wake_in_time_order_at_their_due_time() -> None:
    clock = ManualClock()
    woken: list[tuple[str, float]] = []

    async def sleeper(name: str, seconds: float) -> None:
        await clock.sleep(seconds)
        woken.append((name, clock.monotonic()))

    tasks = [asyncio.create_task(sleeper(name, s)) for name, s in (("c", 3), ("a", 1), ("b", 2))]
    await clock.advance(5)
    assert woken == [("a", 1), ("b", 2), ("c", 3)]
    assert clock.monotonic() == 5
    await asyncio.gather(*tasks)


async def test_periodic_loop_runs_once_per_period() -> None:
    clock = ManualClock()
    ticks: list[float] = []

    async def loop() -> None:
        while True:
            ticks.append(clock.monotonic())
            await clock.sleep(0.5)

    task = asyncio.create_task(loop())
    await clock.advance(10)
    assert ticks == [i * 0.5 for i in range(21)]
    task.cancel()


async def test_cancelled_sleeper_is_skipped() -> None:
    clock = ManualClock()
    task = asyncio.create_task(clock.sleep(1))
    await clock.advance(0)
    assert clock.sleepers == 1
    task.cancel()
    await clock.advance(2)
    assert task.cancelled()
    assert clock.sleepers == 0


async def test_zero_sleep_yields_without_advancing() -> None:
    clock = ManualClock()
    await clock.sleep(0)
    assert clock.monotonic() == 0


async def test_time_cannot_go_backwards() -> None:
    with pytest.raises(ValueError, match="backwards"):
        await ManualClock().advance(-1)


async def test_advancing_does_not_sleep_for_real() -> None:
    clock = ManualClock()
    started = time.monotonic()
    task = asyncio.create_task(clock.sleep(3600))
    await clock.advance(3600)
    assert task.done()
    assert time.monotonic() - started < 1


async def test_system_clock_is_monotonic_and_sleeps() -> None:
    clock: Clock = SystemClock()
    before = clock.monotonic()
    await clock.sleep(0)
    assert clock.monotonic() >= before
    assert abs(clock.wall_time() - time.time()) < 1


def test_manual_clock_satisfies_the_clock_interface() -> None:
    clock: Clock = ManualClock()
    assert clock.monotonic() == 0
