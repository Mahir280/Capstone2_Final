import type { EChartsOption } from "echarts";

import { BaseEChart } from "./BaseEChart";

export interface PieSlice {
  name: string;
  value: number;
  color?: string;
}

interface PieChartProps {
  data: PieSlice[];
  donut?: boolean;
  height?: number;
  ariaLabel?: string;
}

export function PieChart({
  data,
  donut = true,
  height,
  ariaLabel,
}: PieChartProps) {
  const option: EChartsOption = {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { type: "scroll", bottom: 0 },
    grid: { left: 12, right: 16, top: 12, bottom: 36, containLabel: true },
    series: [
      {
        type: "pie",
        radius: donut ? ["42%", "70%"] : "70%",
        center: ["50%", "46%"],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: "#ffffff", borderWidth: 2 },
        label: { formatter: "{b}\n{d}%", color: "#334155" },
        data: data.map((slice) => ({
          name: slice.name,
          value: slice.value,
          itemStyle: slice.color ? { color: slice.color } : undefined,
        })),
      },
    ],
  };

  return <BaseEChart option={option} height={height} ariaLabel={ariaLabel} />;
}
