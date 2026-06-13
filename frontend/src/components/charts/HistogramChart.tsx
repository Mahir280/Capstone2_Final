import type { EChartsOption } from "echarts";

import { BaseEChart } from "./BaseEChart";

export interface HistogramBin {
  label: string;
  count: number;
}

interface HistogramChartProps {
  bins: HistogramBin[];
  valueName?: string;
  color?: string;
  height?: number;
  ariaLabel?: string;
}

export function HistogramChart({
  bins,
  valueName = "Count",
  color = "#0f766e",
  height,
  ariaLabel,
}: HistogramChartProps) {
  const option: EChartsOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "category",
      data: bins.map((bin) => bin.label),
      axisLabel: { interval: 0, rotate: bins.length > 8 ? 30 : 0 },
    },
    yAxis: { type: "value", name: valueName, minInterval: 1 },
    series: [
      {
        type: "bar",
        name: valueName,
        data: bins.map((bin) => bin.count),
        barCategoryGap: "8%",
        itemStyle: { color, borderRadius: [3, 3, 0, 0] },
      },
    ],
  };

  return <BaseEChart option={option} height={height} ariaLabel={ariaLabel} />;
}
