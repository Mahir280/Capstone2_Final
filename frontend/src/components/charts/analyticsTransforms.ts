import type { CountMap, CrossTab } from "../../types/analytics";
import type { ChartTableData } from "./ChartDataTable";
import type { StackedSeries } from "./StackedBarChart";
import type { HistogramBin } from "./HistogramChart";

export interface BarData {
  categories: string[];
  values: number[];
}

// Build an accessible two-column table (category + value) from bar data so a
// chart's numbers stay reachable without the canvas.
export function barToTable(
  caption: string,
  columns: [string, string],
  bar: BarData,
): ChartTableData {
  return {
    caption,
    columns,
    rows: bar.categories.map((category, index) => [category, bar.values[index]]),
  };
}

export function isEmptyMap(map: CountMap | undefined): boolean {
  return !map || Object.keys(map).length === 0;
}

export function isEmptyCrossTab(crossTab: CrossTab | undefined): boolean {
  if (!crossTab) return true;
  return Object.values(crossTab).every(
    (inner) => Object.keys(inner).length === 0,
  );
}

// Count maps from the backend are already sorted (counts desc, or by year asc).
// We preserve that order and optionally cap the number of categories.
export function toBar(map: CountMap, limit?: number): BarData {
  const entries = Object.entries(map);
  const sliced = limit ? entries.slice(0, limit) : entries;
  return {
    categories: sliced.map(([key]) => key),
    values: sliced.map(([, value]) => value),
  };
}

function innerTotals(crossTab: CrossTab): Map<string, number> {
  const totals = new Map<string, number>();
  for (const inner of Object.values(crossTab)) {
    for (const [key, value] of Object.entries(inner)) {
      totals.set(key, (totals.get(key) ?? 0) + value);
    }
  }
  return totals;
}

function topKeys(totals: Map<string, number>, limit?: number): string[] {
  const sorted = [...totals.entries()].sort(
    (a, b) => b[1] - a[1] || a[0].localeCompare(b[0]),
  );
  const sliced = limit ? sorted.slice(0, limit) : sorted;
  return sliced.map(([key]) => key);
}

interface StackedOptions {
  // "outer" puts the cross-tab's outer keys on the category axis and inner keys
  // become stacked series. "inner" flips it.
  axis: "outer" | "inner";
  categoryLimit?: number;
  seriesLimit?: number;
  colorFor?: (name: string) => string;
}

export function crossTabToStacked(
  crossTab: CrossTab,
  options: StackedOptions,
): { categories: string[]; series: StackedSeries[] } {
  const outerKeys = Object.keys(crossTab);
  const innerKeyTotals = innerTotals(crossTab);

  let categories: string[];
  let seriesKeys: string[];
  let lookup: (seriesKey: string, category: string) => number;

  if (options.axis === "outer") {
    categories = options.categoryLimit
      ? outerKeys.slice(0, options.categoryLimit)
      : outerKeys;
    seriesKeys = topKeys(innerKeyTotals, options.seriesLimit);
    lookup = (seriesKey, category) => crossTab[category]?.[seriesKey] ?? 0;
  } else {
    categories = topKeys(innerKeyTotals, options.categoryLimit);
    seriesKeys = options.seriesLimit
      ? outerKeys.slice(0, options.seriesLimit)
      : outerKeys;
    lookup = (seriesKey, category) => crossTab[seriesKey]?.[category] ?? 0;
  }

  const series: StackedSeries[] = seriesKeys.map((seriesKey) => ({
    name: seriesKey,
    data: categories.map((category) => lookup(seriesKey, category)),
    color: options.colorFor ? options.colorFor(seriesKey) : undefined,
  }));

  return { categories, series };
}

export function crossTabToHeatmap(
  crossTab: CrossTab,
  options: { rowLimit?: number; colLimit?: number } = {},
): {
  xCategories: string[];
  yCategories: string[];
  data: Array<[number, number, number]>;
} {
  const rowKeys = Object.keys(crossTab);
  const yCategories = options.rowLimit
    ? rowKeys.slice(0, options.rowLimit)
    : rowKeys;
  const xCategories = topKeys(innerTotals(crossTab), options.colLimit);

  const data: Array<[number, number, number]> = [];
  yCategories.forEach((row, yIndex) => {
    xCategories.forEach((col, xIndex) => {
      const value = crossTab[row]?.[col] ?? 0;
      if (value > 0) data.push([xIndex, yIndex, value]);
    });
  });

  return { xCategories, yCategories, data };
}

// Bin a list of numeric scores into a fixed number of equal-width buckets across
// the observed [min, max] range. Used for the relationship-similarity histogram.
export function buildHistogram(
  values: number[],
  binCount = 10,
): HistogramBin[] {
  if (values.length === 0) return [];
  let min = values[0];
  let max = values[0];
  for (const value of values) {
    if (value < min) min = value;
    if (value > max) max = value;
  }
  if (min === max) {
    return [{ label: min.toFixed(2), count: values.length }];
  }
  const width = (max - min) / binCount;
  const counts = new Array<number>(binCount).fill(0);
  for (const value of values) {
    let index = Math.floor((value - min) / width);
    if (index >= binCount) index = binCount - 1;
    if (index < 0) index = 0;
    counts[index] += 1;
  }
  return counts.map((count, index) => {
    const lower = min + width * index;
    const upper = lower + width;
    return { label: `${lower.toFixed(2)}–${upper.toFixed(2)}`, count };
  });
}
