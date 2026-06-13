import type { EChartsOption } from "echarts";

import { BaseEChart } from "./BaseEChart";

interface BarChartProps {
  categories: string[];
  values: number[];
  horizontal?: boolean;
  valueName?: string;
  color?: string;
  colors?: string[];
  height?: number;
  ariaLabel?: string;
}

export function BarChart({
  categories,
  values,
  horizontal = false,
  valueName = "Patents",
  color,
  colors,
  height,
  ariaLabel,
}: BarChartProps) {
  // Truncate long category labels so dense/narrow axes stay legible. The full
  // category is still shown in the axis tooltip on hover.
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
  const valueAxis = { type: "value" as const, name: valueName };

  const data = colors
    ? values.map((value, index) => ({
        value,
        itemStyle: { color: colors[index % colors.length] },
      }))
    : values;

  const option: EChartsOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? { ...categoryAxis, inverse: true } : valueAxis,
    series: [
      {
        type: "bar",
        name: valueName,
        data,
        barMaxWidth: 36,
        itemStyle: color ? { color, borderRadius: 4 } : { borderRadius: 4 },
      },
    ],
  };

  return <BaseEChart option={option} height={height} ariaLabel={ariaLabel} />;
}
