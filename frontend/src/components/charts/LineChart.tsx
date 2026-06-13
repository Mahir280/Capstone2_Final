import type { EChartsOption } from "echarts";

import { BaseEChart } from "./BaseEChart";

export interface LineSeries {
  name: string;
  data: Array<number | null>;
  color?: string;
}

interface LineChartProps {
  categories: string[];
  series: LineSeries[];
  smooth?: boolean;
  area?: boolean;
  height?: number;
  ariaLabel?: string;
}

export function LineChart({
  categories,
  series,
  smooth = true,
  area = false,
  height,
  ariaLabel,
}: LineChartProps) {
  const showLegend = series.length > 1;
  const option: EChartsOption = {
    tooltip: { trigger: "axis" },
    legend: showLegend ? { type: "scroll", bottom: 0 } : undefined,
    grid: {
      left: 12,
      right: 16,
      top: 28,
      bottom: showLegend ? 36 : 12,
      containLabel: true,
    },
    xAxis: { type: "category", data: categories, boundaryGap: false },
    yAxis: { type: "value" },
    series: series.map((item) => ({
      type: "line" as const,
      name: item.name,
      data: item.data,
      smooth,
      showSymbol: categories.length <= 24,
      connectNulls: false,
      lineStyle: item.color ? { color: item.color, width: 2 } : { width: 2 },
      itemStyle: item.color ? { color: item.color } : undefined,
      areaStyle: area ? { opacity: 0.12 } : undefined,
    })),
  };

  return <BaseEChart option={option} height={height} ariaLabel={ariaLabel} />;
}
