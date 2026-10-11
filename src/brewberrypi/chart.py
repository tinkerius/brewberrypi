"""Temperature chart history (IF-040..044).

One series, sampled every chart period since server start and shared by all clients (IF-042). Only valid
readings are added (IF-041, FIX-17). Above `chart.maxPoints` the history is thinned so that it keeps the
whole time range with decreasing resolution for older data (IF-043).
"""

from typing import Any

from brewberrypi.hal import Temperature

SERIES_KEY = "Kettle Temperature"


class TemperatureChart:
    def __init__(self, max_points: int) -> None:
        self._max_points = max_points
        self._x: list[int] = []
        self._y: list[float] = []

    def sample(self, epoch_seconds: float, temperature: Temperature) -> None:
        """Append a point if the reading is valid, then thin (IF-041, IF-043)."""
        if temperature is None:
            return
        self._x.append(round(epoch_seconds * 1000))
        self._y.append(temperature)
        while len(self._x) > self._max_points:
            self._remove_densest()

    def _remove_densest(self) -> None:
        """Remove point i+1 of the first adjacent pair with the smallest time gap; never the first point."""
        x = self._x
        smallest = min(range(len(x) - 1), key=lambda i: x[i + 1] - x[i])
        del x[smallest + 1]
        del self._y[smallest + 1]

    def data(self) -> list[dict[str, Any]]:
        """ChartData payload (IF-040)."""
        return [
            {"key": SERIES_KEY, "values": [{"x": x, "y": y} for x, y in zip(self._x, self._y, strict=True)]}
        ]

    def __len__(self) -> int:
        return len(self._x)
