"""Temperature chart history (IF-040..044).

One series, sampled every chart period since server start and shared by all clients (IF-042). Only valid
readings are added (IF-041, FIX-17). Above `chart.maxPoints` the history is thinned so that it keeps the
whole time range with decreasing resolution for older data (IF-043). Each sample reports what changed, so
clients get a small update instead of the whole series (IF-044).
"""

from typing import Any

from brewberrypi.hal import Temperature

SERIES_KEY = "Kettle Temperature"


class TemperatureChart:
    def __init__(self, max_points: int) -> None:
        self._max_points = max_points
        self._x: list[int] = []
        self._y: list[float] = []

    def sample(self, epoch_seconds: float, temperature: Temperature) -> dict[str, Any] | None:
        """Append a point if the reading is valid, then thin (IF-041, IF-043).

        Returns the ChartUpdate `{"add": {x, y}, "remove": [x, ...]}`, or `None` if nothing was added.
        """
        if temperature is None:
            return None
        x = round(epoch_seconds * 1000)
        self._x.append(x)
        self._y.append(temperature)
        removed = []
        while len(self._x) > self._max_points:
            removed.append(self._remove_densest())
        return {"add": {"x": x, "y": temperature}, "remove": removed}

    def _remove_densest(self) -> int:
        """Remove point i+1 of the first adjacent pair with the smallest time gap; never the first point.

        Returns its x.
        """
        x = self._x
        smallest = min(range(len(x) - 1), key=lambda i: x[i + 1] - x[i])
        del self._y[smallest + 1]
        return x.pop(smallest + 1)

    def data(self, since: int | None = None) -> list[dict[str, Any]]:
        """ChartData payload (IF-040); with `since`, only the points after that x (epoch milliseconds)."""
        points = zip(self._x, self._y, strict=True)
        values = [{"x": x, "y": y} for x, y in points if since is None or x > since]
        return [{"key": SERIES_KEY, "values": values}]

    def __len__(self) -> int:
        return len(self._x)
