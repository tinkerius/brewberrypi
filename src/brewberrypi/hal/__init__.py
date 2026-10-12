"""Hardware abstraction layer (HW-001..003, NFR-062).

All hardware access goes through `Hal`. Implementations: `MockHal` for unit tests (`hal.mock`), the
simulation for `--dummymode` (M6) and the Raspberry Pi (M9). Every implementation must be thread-safe
(HW-003): the engine loop, command handlers, broadcast loops and shutdown all call it.
"""

from abc import ABC, abstractmethod

Temperature = float | None
"""A kettle temperature in °C, or `None` for INVALID (HW-032). Callers must handle `None` (FIX-02)."""

BeepPattern = tuple[tuple[bool, int], ...]
"""Buzzer phases as (on, milliseconds)."""

SHORT_BEEP: BeepPattern = ((True, 500),)
"""HW-040."""
LONG_BEEP: BeepPattern = (
    (True, 2000),
    (False, 300),
    (True, 200),
    (False, 300),
    (True, 200),
    (False, 300),
    (True, 200),
    (False, 300),
    (True, 2000),
)
"""HW-041, the attention pattern (about 5.8 s)."""
ERROR_BEEP: BeepPattern = ((True, 500),)
"""HW-042."""


class Hal(ABC):
    """The operations of HW-001, nothing else."""

    @abstractmethod
    def switch_on_pump(self) -> None:
        """Pump relay on. Idempotent."""

    @abstractmethod
    def switch_off_pump(self) -> None:
        """Pump relay off. Idempotent."""

    @abstractmethod
    def get_pump_status(self) -> bool:
        """`True` if the pump is on."""

    @abstractmethod
    def set_heating(self, power: float) -> None:
        """Request heating power 0..1; implementations store `clamp_power(power)` (CTL-040..046)."""

    @abstractmethod
    def get_heating_status(self) -> float:
        """The last requested heating power, after clamping."""

    @abstractmethod
    def get_temperature(self) -> Temperature:
        """The latest cached kettle temperature, or `None` (INVALID). Never blocks on I/O (HW-030)."""

    @abstractmethod
    def short_beep(self) -> None:
        """Non-blocking short beep (HW-040)."""

    @abstractmethod
    def long_beep(self) -> None:
        """Non-blocking attention pattern (HW-041)."""

    @abstractmethod
    def switch_everything_off(self) -> None:
        """Heating 0 and pump off."""

    # Lifecycle, not part of HW-001; the application calls them once on startup and shutdown.

    async def start(self) -> None:  # noqa: B027  (optional hook)
        """Start background work (sensor loop) and wait for the first reading (HW-030, HW-034)."""

    async def close(self) -> None:
        """Everything off and resources released (HW-021)."""
        self.switch_everything_off()


def clamp_power(power: float) -> float:
    """Clamp a heating power to [0, 1] (HW-001). Anything that is not a number above 0, NaN included, is 0."""
    if not power > 0:
        return 0.0
    return min(power, 1.0)
