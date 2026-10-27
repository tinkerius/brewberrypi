/** Chart panel content (UI-020..023): uPlot line chart of the kettle temperature. */

import { useEffect, useRef } from "preact/hooks";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import { formatDegrees, formatTime, formatTimeWithSeconds } from "./format";
import type { ChartSeries } from "./types";

export const SERIES_LABEL = "Kettle Temperature";
const HEIGHT = 300;

/** IF-040 points (x in epoch milliseconds) as uPlot columns (x in epoch seconds). */
export function toPlotData(series: ChartSeries[] | null): [number[], number[]] {
  const values = series?.[0]?.values ?? [];
  return [values.map((point) => point.x / 1000), values.map((point) => point.y)];
}

const GRID = "rgba(128, 128, 128, 0.25)";

/** `text` is the page's text colour and `line` the brand's berry for the scheme in use (the container's
 * `--chart-line`), so axes and line stay readable in the light and the dark scheme. */
function options(width: number, text: string, line: string): uPlot.Options {
  const axis = { stroke: text, grid: { stroke: GRID }, ticks: { stroke: GRID } };
  return {
    width,
    height: HEIGHT,
    scales: { x: { time: true } },
    axes: [
      { ...axis, label: "Time", values: (_plot, ticks) => ticks.map(formatTime) },
      { ...axis, label: "Temperature", values: (_plot, ticks) => ticks.map(formatDegrees) },
    ],
    series: [
      { value: (_plot, value) => (value == null ? "--" : formatTimeWithSeconds(value)) },
      {
        label: SERIES_LABEL,
        stroke: line,
        width: 2,
        value: (_plot, value) => (value == null ? "--" : `${formatDegrees(value)}°C`),
      },
    ],
  };
}

export function Chart(props: { series: ChartSeries[] | null }) {
  const container = useRef<HTMLDivElement>(null);
  const plot = useRef<uPlot | null>(null);

  useEffect(() => {
    const element = container.current;
    if (element === null) {
      return;
    }
    // Created once and only fed new data afterwards (UI-023); empty until the first message (UI-022).
    const style = getComputedStyle(element);
    const line = style.getPropertyValue("--chart-line").trim() || "#8a2a4a";
    const chart = new uPlot(options(element.clientWidth || 600, style.color, line), toPlotData(null), element);
    plot.current = chart;
    const resize = new ResizeObserver(() => chart.setSize({ width: element.clientWidth, height: HEIGHT }));
    resize.observe(element);
    return () => {
      resize.disconnect();
      chart.destroy();
      plot.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = plot.current;
    if (chart === null) {
      return;
    }
    // Keep a zoom the user selected (UI-023); a double click on the chart resets it.
    const shown = chart.data[0];
    const scale = chart.scales.x;
    const zoomed =
      shown.length > 1 && scale.min != null && scale.max != null && (scale.min > shown[0] || scale.max < shown[shown.length - 1]);
    chart.setData(toPlotData(props.series), !zoomed);
  }, [props.series]);

  return <div class="min-h-[300px] w-full [--chart-line:var(--color-berry)] dark:[--chart-line:var(--color-berry-light)]" ref={container} />;
}
