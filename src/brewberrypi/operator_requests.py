"""Operator requests and the reminder loop (DOM-030..034).

A goal that needs the brewer creates a request; the brewer answers it with one of its options. While a request
is active and unanswered, `RequestReminder` plays the long beep immediately and then every reminder interval.
"""

import asyncio
from typing import ClassVar

from brewberrypi.clock import Clock
from brewberrypi.hal import Hal


class InvalidResponse(ValueError):
    """The answer is not one of the request's options (DOM-032, FIX-11). The message is the reply text."""


class OperatorRequest:
    """A question or instruction with an ordered list of answer options (DOM-030)."""

    options: ClassVar[tuple[str, ...]]

    def __init__(self, message: str) -> None:
        self.message = message
        self.answer: str | None = None
        """The chosen option, `None` while unanswered."""

    @property
    def answered(self) -> bool:
        return self.answer is not None

    def respond(self, option: str) -> None:
        """Record the answer; matched case-sensitively (DOM-032).

        An answer given before the goal has processed the previous one replaces it.
        """
        if option not in self.options:
            raise InvalidResponse(f"Response option '{option}' is not valid.")
        self.answer = option


class ConfirmationRequest(OperatorRequest):
    options = ("Confirm",)

    @property
    def confirmed(self) -> bool:
        return self.answer == "Confirm"


class YesNoDecisionRequest(OperatorRequest):
    options = ("Yes", "No")

    @property
    def yes(self) -> bool:
        return self.answer == "Yes"

    @property
    def no(self) -> bool:
        return self.answer == "No"


class RequestReminder:
    """The single reminder loop (DOM-033, FIX-12).

    The engine calls `follow()` with the active goal's request after every tick and every command, and with
    `None` when the process is paused, stopped or unloaded. The loop runs only for an unanswered request;
    a different request restarts it with an immediate long beep.
    """

    def __init__(self, hal: Hal, clock: Clock, interval_seconds: float) -> None:
        self._hal = hal
        self._clock = clock
        self._interval = interval_seconds
        self._request: OperatorRequest | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._task is not None

    def follow(self, request: OperatorRequest | None) -> None:
        wanted = request if request is not None and not request.answered else None
        if wanted is self._request:
            return
        self.stop()
        if wanted is not None:
            self._request = wanted
            self._hal.long_beep()
            self._task = asyncio.get_running_loop().create_task(self._remind())

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
        self._task = None
        self._request = None

    async def _remind(self) -> None:
        while True:
            await self._clock.sleep(self._interval)
            self._hal.long_beep()
