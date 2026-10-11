"""M7: chart history (IF-040..044, AC-073, AC-074)."""

import itertools

from brewberrypi.chart import TemperatureChart
from brewberrypi.web.messages import validator

CHART_DATA = validator("ChartData")


def xs(chart: TemperatureChart) -> list[int]:
    return [point["x"] for point in chart.data()[0]["values"]]


def test_IF_041_points_are_epoch_milliseconds_and_degrees() -> None:
    chart = TemperatureChart(200)
    chart.sample(1_718_197_200.0, 62.5)
    assert chart.data() == [{"key": "Kettle Temperature", "values": [{"x": 1_718_197_200_000, "y": 62.5}]}]
    CHART_DATA(chart.data())


def test_AC_074_invalid_readings_are_not_added() -> None:
    chart = TemperatureChart(200)
    chart.sample(1.0, 20.0)
    chart.sample(2.0, None)
    chart.sample(3.0, 0.0)  # a valid reading of 0 °C is kept (legacy dropped everything <= 0)
    assert xs(chart) == [1000, 3000]


def test_AC_073_thinning_removes_the_point_after_the_smallest_gap() -> None:
    chart = TemperatureChart(200)
    times: list[float] = []
    t = 0.0
    for number in range(1, 202):  # points 1..201
        times.append(t)
        chart.sample(t, 20.0)
        t += 0.2 if number == 50 else 1.0  # the gap between points 50 and 51 is 0.2 s
    assert len(chart) == 200
    point_51 = round(times[50] * 1000)
    assert point_51 not in xs(chart)
    assert xs(chart) == [round(x * 1000) for i, x in enumerate(times) if i != 50]


def test_IF_043_ties_remove_the_first_pair_and_never_the_first_point() -> None:
    chart = TemperatureChart(3)
    for t in (0, 1, 2, 3):
        chart.sample(t, 20.0)
    assert xs(chart) == [0, 2000, 3000]  # equal gaps: the first pair (0, 1) loses point 1
    chart.sample(4, 20.0)
    assert xs(chart) == [0, 2000, 4000]  # gaps 2, 1, 1: the first smallest pair (2, 3) loses point 3
    chart.sample(5, 20.0)
    assert xs(chart) == [0, 2000, 4000]  # gaps 2, 2, 1: the newest point itself is removed (see Q-24)
    for t in (6, 7, 8, 9):
        chart.sample(t, 20.0)
    assert xs(chart)[0] == 0  # the first point is never removed
    assert len(chart) == 3


def test_IF_043_long_history_keeps_the_range_with_coarser_old_data() -> None:
    chart = TemperatureChart(200)
    for t in range(3600):
        chart.sample(t, 20.0)
    points = xs(chart)
    assert len(points) == 200
    assert points[0] == 0
    assert points[-1] >= 3_599_000 - 16_000  # the newest point lags by at most the newest gap (Q-24)
    gaps = [b - a for a, b in itertools.pairwise(points)]
    assert gaps[0] >= gaps[-1]  # older data is thinner
