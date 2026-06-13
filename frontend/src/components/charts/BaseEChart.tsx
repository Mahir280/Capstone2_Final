import { useEffect, useMemo, useRef } from "react";
import type { EChartsType } from "echarts/core";
import type { EChartsOption } from "echarts";

import { echarts } from "./echartsCore";
import { ANALYTICS_THEME, baseOptions, ensureAnalyticsTheme } from "./echartsTheme";

interface BaseEChartProps {
  option: EChartsOption;
  height?: number;
  ariaLabel?: string;
}

function mergeOption(option: EChartsOption): EChartsOption {
  const base = baseOptions();
  return {
    ...base,
    ...option,
    grid: option.grid ?? base.grid,
    tooltip: { ...base.tooltip, ...(option.tooltip as object) },
    textStyle: { ...base.textStyle, ...(option.textStyle as object) },
  };
}

export function BaseEChart({ option, height = 320, ariaLabel }: BaseEChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<EChartsType | null>(null);
  const merged = useMemo(() => mergeOption(option), [option]);

  // Initialise the chart instance once the container is mounted, and dispose it
  // on unmount. A ResizeObserver keeps the canvas sized to its container.
  useEffect(() => {
    ensureAnalyticsTheme();
    const container = containerRef.current;
    if (!container) return undefined;

    const chart = echarts.init(container, ANALYTICS_THEME, { renderer: "canvas" });
    chartRef.current = chart;

    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  // Push option updates to the live instance.
  useEffect(() => {
    chartRef.current?.setOption(merged, true);
  }, [merged]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
      className="chart-canvas"
      style={{ height, width: "100%" }}
    />
  );
}
