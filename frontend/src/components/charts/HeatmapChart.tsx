import type { EChartsOption } from "echarts";

import { BaseEChart } from "./BaseEChart";

interface HeatmapChartProps {
  xCategories: string[];
  yCategories: string[];
  // Tuples of [xIndex, yIndex, value].
  data: Array<[number, number, number]>;
  height?: number;
  ariaLabel?: string;
}

export function HeatmapChart({
  xCategories,
  yCategories,
  data,
  height,
  ariaLabel,
}: HeatmapChartProps) {
  const maxValue = data.reduce((max, [, , value]) => Math.max(max, value), 0);

  const option: EChartsOption = {
    tooltip: {
      position: "top",
      formatter: (params: unknown) => {
        const point = params as { value: [number, number, number] };
        const [x, y, value] = point.value;
        return `${yCategories[y]} · ${xCategories[x]}: ${value}`;
      },
    },
    grid: { left: 12, right: 16, top: 12, bottom: 72, containLabel: true },
    xAxis: {
      type: "category",
      data: xCategories,
      splitArea: { show: true },
      // Rotate + truncate crowded column labels; full label stays in the tooltip.
      axisLabel: {
        interval: 0,
        rotate: xCategories.length > 6 ? 45 : 0,
        width: 90,
        overflow: "truncate",
        hideOverlap: true,
      },
    },
    yAxis: {
      type: "category",
      data: yCategories,
      splitArea: { show: true },
      // Truncate long row labels (assignee / keyword names); tooltip shows full.
      axisLabel: { width: 120, overflow: "truncate" },
    },
    visualMap: {
      min: 0,
      max: maxValue || 1,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: { color: ["#eef4ff", "#3b82f6", "#1d3fbf"] },
    },
    series: [
      {
        type: "heatmap",
        data,
        label: { show: maxValue > 0 },
        emphasis: {
          itemStyle: { shadowBlur: 8, shadowColor: "rgba(15,23,42,0.25)" },
        },
      },
    ],
  };

  return <BaseEChart option={option} height={height} ariaLabel={ariaLabel} />;
}
