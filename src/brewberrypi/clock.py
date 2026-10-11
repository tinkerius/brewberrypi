"""Clocks (NFR-005, NFR-060).

All timing-critical logic (countdowns, duty cycle, staleness, loop pacing) takes a `Clock` and uses its
monotonic time and `sleep()`, never `time.time()` or `asyncio.sleep()` directly. Wall-clock time is only for
chart timestamps and logs. Production code uses `SystemClock`; unit tests use `ManualClock` and move time
forward explicitly, so no test sleeps for real.
"""

import asyncio
import heapq
import itertools
import time
from typing import Protocol


class Clock(Protocol):
    def monotonic(self) -> float:
        """Seconds on a clock that never jumps (NFR-005). Only differences are meaningful."""
        ...

    def wall_time(self) -> float:
        """Seconds since the Unix epoch; for chart timestamps and logs only."""
        ...

    async def sleep(self, seconds: float) -> None:
        """Wait `seconds` of this clock's time."""
        ...


class SystemClock:
    """The real clock."""

    def monotonic(self) -> float:
        return time.monotonic()

    def wall_time(self) -> float:
        return time.time()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


# Event-loop iterations `ManualClock` grants after each wake-up, so that woken tasks can run until they wait
# again. A task that needs more steps than this between two sleeps must be awaited explicitly by the test.
SETTLE_ROUNDS = 50


class ManualClock:
    """A clock that only moves when a test calls `advance()` (NFR-060).

    `sleep()` waits until `advance()` has moved the time past the sleeper's due time. `advance()` wakes the
    sleepers in time order and sets `monotonic()` to each due time before waking it, so a loop that sleeps
    0.5 s per iteration runs exactly 20 iterations, each at the right time, when the test advances 10 s.
    """

    def __init__(self, start: float = 0.0, wall_start: float = 1_800_000_000.0) -> None:
        self._now = start
        self._wall_offset = wall_start - start
        self._sleepers: list[tuple[float, int, asyncio.Future[None]]] = []
        self._order = itertools.count()

    def monotonic(self) -> float:
        return self._now

    def wall_time(self) -> float:
        return self._now + self._wall_offset

    async def sleep(self, seconds: float) -> None:
        if seconds <= 0:
            await asyncio.sleep(0)
            return
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        heapq.heappush(self._sleepers, (self._now + seconds, next(self._order), future))
        await future

    async def advance(self, seconds: float) -> None:
        """Move the time forward by `seconds`, waking every sleeper that becomes due on the way."""
        if seconds < 0:
            raise ValueError("a monotonic clock cannot go backwards")
        target = self._now + seconds
        await _settle()
        while self._sleepers and self._sleepers[0][0] <= target:
            due, _, future = heapq.heappop(self._sleepers)
            if future.done():  # the sleeping task was cancelled
                continue
            self._now = max(self._now, due)
            future.set_result(None)
            await _settle()
        self._now = target
        await _settle()

    @property
    def sleepers(self) -> int:
        """Number of tasks currently waiting in `sleep()`."""
        return sum(1 for _, _, future in self._sleepers if not future.done())


async def _settle() -> None:
    for _ in range(SETTLE_ROUNDS):
        await asyncio.sleep(0)
