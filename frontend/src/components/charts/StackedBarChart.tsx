import type { EChartsOption } from "echarts";

import { BaseEChart } from "./BaseEChart";

export interface StackedSeries {
  name: string;
  data: number[];
  color?: string;
}

interface StackedBarChartProps {
  categories: string[];
  series: StackedSeries[];
  horizontal?: boolean;
  height?: number;
  ariaLabel?: string;
}

export function StackedBarChart({
  categories,
  series,
  horizontal = false,
  height,
  ariaLabel,
}: StackedBarChartProps) {
  // Truncate long category labels so dense/narrow axes stay legible. Full
  // labels remain available via the axis tooltip on hover.
  const categoryAxis = {
    type: "category" as const,
    data: categories,
    axisLabel: horizontal
      ? { width: 150, overflow: "truncate" as const }
      : {
          interval: 0,
          rotate: categories.length > 8 ? 35 : 0,
          width: 88,
          overflow: "truncate" as const,
        },
  };
  const valueAxis = { type: "value" as const };

  const option: EChartsOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { type: "scroll", bottom: 0 },
    grid: { left: 12, right: 16, top: 28, bottom: 36, containLabel: true },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? { ...categoryAxis, inverse: true } : valueAxis,
    series: series.map((item) => ({
      type: "bar" as const,
      name: item.name,
      stack: "total",
      data: item.data,
      barMaxWidth: 48,
      emphasis: { focus: "series" as const },
      itemStyle: item.color ? { color: item.color } : undefined,
    })),
  };

  return <BaseEChart option={option} height={height} ariaLabel={ariaLabel} />;
}
