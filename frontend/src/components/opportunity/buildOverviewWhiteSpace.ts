import type { AnalyticsResponse } from "../../types/analytics";

// Derive "underexplored areas" from existing analytics without adding another
// model. Candidate application areas with comparatively few records in the
// filtered view are paired with recent-activity context so the result remains
// an exploratory signal rather than a market guarantee.

export interface WhiteSpaceArea {
  name: string;
  count: number;
}

export interface OverviewWhiteSpace {
  /** Lowest-coverage candidate application areas in the current view. */
  areas: WhiteSpaceArea[];
  /** Distinct candidate application areas observed in view (within the cap). */
  totalAreas: number;
  /** Median per-area record count, shown for honest context. */
  medianCount: number;
  /** Highest per-area record count, shown for honest context. */
  maxCount: number;
  /** Share of in-view records published in the recent window (0–1), if known. */
  recentShare: number | null;
  /** The recent publication-year window the share was computed over. */
  recentWindow: { from: number; to: number } | null;
}

const MAX_WHITE_SPACE_AREAS = 6;
const RECENT_WINDOW_YEARS = 3;

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid];
}

function recentContext(
  data: AnalyticsResponse,
): { recentShare: number | null; recentWindow: { from: number; to: number } | null } {
  const yearEntries = Object.entries(data.trends.by_publication_year)
    .map(([year, count]) => ({ year: Number(year), count }))
    .filter((entry) => Number.isFinite(entry.year) && entry.count > 0);
  if (yearEntries.length === 0) {
    return { recentShare: null, recentWindow: null };
  }
  const total = yearEntries.reduce((acc, entry) => acc + entry.count, 0);
  if (total === 0) return { recentShare: null, recentWindow: null };
  const maxYear = yearEntries.reduce(
    (acc, entry) => (entry.year > acc ? entry.year : acc),
    yearEntries[0].year,
  );
  const from = maxYear - (RECENT_WINDOW_YEARS - 1);
  const recentTotal = yearEntries
    .filter((entry) => entry.year >= from)
    .reduce((acc, entry) => acc + entry.count, 0);
  return {
    recentShare: recentTotal / total,
    recentWindow: { from, to: maxYear },
  };
}

export function buildOverviewWhiteSpace(
  data: AnalyticsResponse,
): OverviewWhiteSpace {
  const areaEntries = Object.entries(data.technology.application_areas).filter(
    ([, count]) => count > 0,
  );
  const counts = areaEntries.map(([, count]) => count);
  const med = median(counts);
  const maxCount = counts.length > 0 ? Math.max(...counts) : 0;

  // Flag areas at or below half the median per-area count (a relative
  // sparseness rule that adapts to corpus size), capped to a short, scannable
  // list ordered from sparsest first.
  const threshold = Math.max(1, Math.floor(med / 2) || 1);
  const areas = areaEntries
    .filter(([, count]) => count <= threshold)
    .sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]))
    .slice(0, MAX_WHITE_SPACE_AREAS)
    .map(([name, count]) => ({ name, count }));

  const { recentShare, recentWindow } = recentContext(data);

  return {
    areas,
    totalAreas: areaEntries.length,
    medianCount: med,
    maxCount,
    recentShare,
    recentWindow,
  };
}
