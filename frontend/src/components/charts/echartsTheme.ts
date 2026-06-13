import type { EChartsOption } from "echarts";

import { echarts } from "./echartsCore";

// Palette derived from the light-theme design tokens in global.css so charts
// stay visually consistent with the rest of the app (theme choice A).
//   --color-primary #1d3fbf, --color-accent #0f766e, info/success/warning/error
//   semantic families, plus a few harmonising shades for longer categories.
export const CHART_PALETTE = [
  "#1d3fbf", // primary
  "#0f766e", // accent (teal)
  "#3b82f6", // info blue
  "#f59e0b", // warning amber
  "#10b981", // success green
  "#ef4444", // error red
  "#6366f1", // indigo
  "#0ea5e9", // sky
  "#a855f7", // violet
  "#14b8a6", // teal-light
  "#eab308", // gold
  "#64748b", // slate
];

// Stable per-source colors so an authority keeps the same hue across every
// chart. The backend echoes authority labels such as "TURKPATENT/TPO", so we
// match on a normalised prefix.
const SOURCE_COLORS: Array<[RegExp, string]> = [
  [/^USPTO/i, "#1d3fbf"],
  [/^EPO/i, "#0f766e"],
  [/^TURKPATENT/i, "#f59e0b"],
];

export function colorForSource(label: string): string {
  for (const [pattern, color] of SOURCE_COLORS) {
    if (pattern.test(label)) return color;
  }
  return CHART_PALETTE[0];
}

const TOKENS = {
  text: "#0f172a",
  text2: "#334155",
  textMuted: "#5b6473",
  border: "#dde3ee",
  surface: "#ffffff",
  surface2: "#f4f6fb",
  axisLine: "#c4cdde",
  splitLine: "#e6eaf2",
};

const FONT_FAMILY =
  '"Inter", "Segoe UI", system-ui, -apple-system, sans-serif';

export const ANALYTICS_THEME = "fiber-analytics";

let themeRegistered = false;

export function ensureAnalyticsTheme(): void {
  if (themeRegistered) return;
  echarts.registerTheme(ANALYTICS_THEME, {
    color: CHART_PALETTE,
    backgroundColor: "transparent",
    textStyle: { fontFamily: FONT_FAMILY, color: TOKENS.text2 },
    title: {
      textStyle: { color: TOKENS.text, fontWeight: 600 },
      subtextStyle: { color: TOKENS.textMuted },
    },
    legend: { textStyle: { color: TOKENS.text2 } },
    categoryAxis: {
      axisLine: { lineStyle: { color: TOKENS.axisLine } },
      axisTick: { lineStyle: { color: TOKENS.axisLine } },
      axisLabel: { color: TOKENS.textMuted },
      splitLine: { lineStyle: { color: TOKENS.splitLine } },
    },
    valueAxis: {
      axisLine: { lineStyle: { color: TOKENS.axisLine } },
      axisLabel: { color: TOKENS.textMuted },
      splitLine: { lineStyle: { color: TOKENS.splitLine } },
    },
    tooltip: {
      backgroundColor: TOKENS.surface,
      borderColor: TOKENS.border,
      textStyle: { color: TOKENS.text },
    },
  });
  themeRegistered = true;
}

// Common option fragments every chart merges in for a consistent look.
export function baseOptions(): EChartsOption {
  return {
    grid: { left: 12, right: 16, top: 28, bottom: 12, containLabel: true },
    tooltip: {
      confine: true,
      textStyle: { fontFamily: FONT_FAMILY },
    },
    textStyle: { fontFamily: FONT_FAMILY },
  };
}
