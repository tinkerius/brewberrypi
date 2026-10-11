"""Goals: the steps of a brew process (DOM-020..023, spec 04).

`create_goal()` turns a recipe goal definition into a fresh goal instance (DOM-011). The engine (M5) calls
`pursue()` once per tick while the goal is `Active` and marks it `Done` with `complete()` when `pursue()`
returns `True`. Texts are verbatim from the specification, including legacy spellings (Q-07).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeVar

from brewberrypi.config import ControlConfig
from brewberrypi.control import SENSOR_ERROR, Countdown, Progress, TemperatureController
from brewberrypi.hal import Hal
from brewberrypi.operator_requests import ConfirmationRequest, OperatorRequest, YesNoDecisionRequest
from brewberrypi.recipes import GoalDefinition, GoalType

GoalState = Literal["Waiting", "Active", "Done"]

HOPS_COOKING_TEMPERATURE = 97.0
COOK_WATER_TEMPERATURE = 100.0
WAITING_FOR_ANSWER = "Waiting for answer"


@dataclass(frozen=True)
class GoalContext:
    """What goals need from the outside."""

    hal: Hal
    control: ControlConfig
    running_time: Callable[[], float]
    """Seconds of running time, standing still while paused (`control.RunningTime`, ENG-030)."""


def _degrees(temperature: float) -> str:
    """Temperatures in texts have one decimal place, like the legacy Java formatting (`62.0`)."""
    return f"{temperature:.1f}"


class Goal(ABC):
    """One step of a brew process (DOM-020)."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.status: GoalState = "Waiting"
        self.active_request: OperatorRequest | None = None

    @abstractmethod
    def pursue(self) -> bool:
        """One tick of work while `Active`; `True` when the goal is achieved."""

    def activate(self) -> None:
        self.status = "Active"

    def complete(self) -> None:
        """Mark the goal `Done` and remove its request (DOM-023)."""
        self.status = "Done"
        self.active_request = None

    @property
    def progress(self) -> Progress:
        """`statusPercent` and `statusMessage`; default progress of DOM-022."""
        return Progress(100, "100%") if self.status == "Done" else Progress(0, "0%")

    @property
    def status_percent(self) -> int:
        return self.progress.percent

    @property
    def status_message(self) -> str:
        return self.progress.message


class ConfirmationGoal(Goal):
    """Waits for the brewer to confirm a manual step; actuators unchanged (GOAL-001, GOAL-003)."""

    def __init__(self, name: str, description: str, request_message: str) -> None:
        super().__init__(name, description)
        self._request_message = request_message

    def pursue(self) -> bool:
        request = self.active_request
        if not isinstance(request, ConfirmationRequest):
            self.active_request = ConfirmationRequest(self._request_message)
            return False
        return request.confirmed


class PourInBrewingWater(ConfirmationGoal):
    """GOAL-001."""

    def __init__(self) -> None:
        super().__init__("Add Water", "Pour in the brewing water.", "Pour in brewing water")


class MashIn(ConfirmationGoal):
    """GOAL-003: the temperature is not held while waiting (legacy, Q-03)."""

    def __init__(self) -> None:
        super().__init__("Mash In", "Now it's your job to mash in the malt.", "Mash in now")


class Lautering(ConfirmationGoal):
    """GOAL-006: everything off on every tick, then wait for confirmation."""

    def __init__(self, hal: Hal) -> None:
        super().__init__("Lautering", "Now it's your job to lauter.", "Lauter now")
        self._hal = hal

    def pursue(self) -> bool:
        self._hal.switch_everything_off()
        return super().pursue()


class HeatUp(Goal):
    """GOAL-002 (and GOAL-007 with boost): heat to the target; progress by temperature."""

    def __init__(self, context: GoalContext, temperature: float, boost: bool = False) -> None:
        description = (
            "Heat up mash for cooking" if boost else f"Heat up mash to {_degrees(temperature)} degrees (C)."
        )
        super().__init__("Heat Up", description)
        self.temperature = temperature
        self._boost = boost
        self._controller = TemperatureController(context.hal, context.control)

    def pursue(self) -> bool:
        return self._controller.hold(self.temperature, boost=self._boost)

    @property
    def progress(self) -> Progress:
        return self._controller.progress if self.status == "Active" else super().progress


class Rest(Goal):
    """GOAL-004 (and GOAL-008 CookWater): hold the temperature for a time; progress by time."""

    def __init__(
        self,
        context: GoalContext,
        temperature: float,
        minutes: int,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            "Rest" if name is None else name,
            f"Rest at {_degrees(temperature)} degrees (C) for {minutes}min."
            if description is None
            else description,
        )
        self.temperature = temperature
        self._controller = TemperatureController(context.hal, context.control)
        self._countdown = Countdown(minutes, context.running_time)

    def pursue(self) -> bool:
        self._controller.hold(self.temperature)
        return self._countdown.elapsed()

    @property
    def progress(self) -> Progress:
        if self.status != "Active":
            return super().progress
        progress = self._countdown.progress
        if self._controller.progress.message == SENSOR_ERROR:
            return Progress(progress.percent, SENSOR_ERROR)  # AC-005: the goal shows the sensor error
        return progress


class IodineTest(Goal):
    """GOAL-005: hold the temperature (FIX-13) and ask; on "No" rest another M minutes and ask again."""

    def __init__(self, context: GoalContext, temperature: float, minutes: int) -> None:
        super().__init__("Iodine Test", "Now it's your job to do the iodine test.")
        self.temperature = temperature
        self.minutes = minutes
        self.additional_rest = False
        self._controller = TemperatureController(context.hal, context.control)
        self._countdown = Countdown(minutes, context.running_time)

    def pursue(self) -> bool:
        self._controller.hold(self.temperature)
        if self.additional_rest:
            if self._countdown.elapsed():
                self._countdown.reset()
                self.additional_rest = False
            return False
        request = self.active_request
        if not isinstance(request, YesNoDecisionRequest):
            self.active_request = YesNoDecisionRequest("Iodine test successfull?")
            return False
        if request.yes:
            return True
        if request.no:
            self.active_request = None
            self.additional_rest = True
            self.description += f"\nRest at {_degrees(self.temperature)} degrees (C) for {self.minutes}min."
        return False

    @property
    def progress(self) -> Progress:
        if self.status != "Active":
            return super().progress  # Q-23
        if self._controller.progress.message == SENSOR_ERROR:
            percent = self._countdown.progress.percent if self.additional_rest else 0
            return Progress(percent, SENSOR_ERROR)
        if self.additional_rest:
            return self._countdown.progress
        return Progress(0, WAITING_FOR_ANSWER)


_FACTORIES: dict[GoalType, Callable[[GoalDefinition, GoalContext], Goal]] = {
    "PourInBrewingWater": lambda d, c: PourInBrewingWater(),
    "HeatUp": lambda d, c: HeatUp(c, _required(d.temperature)),
    "MashIn": lambda d, c: MashIn(),
    "Rest": lambda d, c: Rest(c, _required(d.temperature), _required(d.minutes), d.name, d.description),
    "IodineTest": lambda d, c: IodineTest(c, _required(d.temperature), _required(d.minutes)),
    "Lautering": lambda d, c: Lautering(c.hal),
    "HeatUpForHopsCooking": lambda d, c: HeatUp(c, HOPS_COOKING_TEMPERATURE, boost=True),
    "CookWater": lambda d, c: Rest(c, COOK_WATER_TEMPERATURE, _required(d.minutes), d.name, d.description),
}


def create_goal(definition: GoalDefinition, context: GoalContext) -> Goal:
    """A fresh goal instance for a recipe goal definition (DOM-011, GOAL-100)."""
    return _FACTORIES[definition.type](definition, context)


_T = TypeVar("_T")


def _required(value: _T | None) -> _T:
    """Parameters the recipe schema guarantees for this goal type (RCP-003)."""
    if value is None:
        raise ValueError("goal parameter missing; the recipe file was not validated")
    return value
