import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useSearchParams } from "react-router-dom";

import { compactParams } from "../api/landscape";
import {
  landscapeFormFromQuery,
  type LandscapeFilterFormState,
} from "../components/filters/patentFilterModel";
import type {
  LandscapeActiveFilters,
  LandscapeQuery,
} from "../types/landscape";

// These patent-filter facets make up the shared cross-page filter state.
// Map-only graph-tuning parameters stay local to the Map view because they
// affect graph rendering rather than corpus selection. The top-bar `q` search
// parameter belongs to the separate Search workflow and is also left untouched.
const PATENT_FILTER_KEYS = [
  "source",
  "publication_year_from",
  "publication_year_to",
  "filing_year_from",
  "filing_year_to",
  "country",
  "assignee",
  "keyword",
  "application_area",
  "classification",
] as const;

export interface FilterContextValue {
  /** Applied patent filters (graph params excluded), derived from the URL. */
  filters: LandscapeQuery;
  /** The same applied filters expressed as the editable form shape. */
  form: LandscapeFilterFormState;
  /** The applied filters in the active-filter shape for chips/summaries. */
  activeFilters: LandscapeActiveFilters;
  /** True when any patent filter is currently active. */
  hasActiveFilters: boolean;
  /**
   * The active filters encoded as a bare query string (no leading `?`, filter
   * params only). Filter-aware navigation appends this value so filters persist
   * across Overview, Map, and Trends and remain shareable.
   */
  filterSearch: string;
  /** Commit a new applied filter set; writes the URL (pushes a history entry). */
  setFilters: (query: LandscapeQuery) => void;
  /** Clear every patent filter from the shared state and the URL. */
  resetFilters: () => void;
}

const FilterContext = createContext<FilterContextValue | null>(null);

function readNumberParam(
  params: URLSearchParams,
  key: string,
): number | undefined {
  const raw = params.get(key);
  if (raw === null || raw.trim() === "") return undefined;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function readTextParam(
  params: URLSearchParams,
  key: string,
): string | undefined {
  const raw = params.get(key);
  if (raw === null) return undefined;
  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function readListParam(params: URLSearchParams, key: string): string[] {
  return params
    .getAll(key)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

// URL query string -> applied patent-filter query. The inverse of
// writeFiltersToParams; together they make the URL the source of truth so a
// filtered view is shareable and survives reload / back-forward.
export function parseFiltersFromParams(params: URLSearchParams): LandscapeQuery {
  const query: LandscapeQuery = {};

  const sources = readListParam(params, "source");
  if (sources.length > 0) query.source = sources;

  const publicationYearFrom = readNumberParam(params, "publication_year_from");
  if (publicationYearFrom !== undefined) {
    query.publication_year_from = publicationYearFrom;
  }
  const publicationYearTo = readNumberParam(params, "publication_year_to");
  if (publicationYearTo !== undefined) {
    query.publication_year_to = publicationYearTo;
  }
  const filingYearFrom = readNumberParam(params, "filing_year_from");
  if (filingYearFrom !== undefined) query.filing_year_from = filingYearFrom;
  const filingYearTo = readNumberParam(params, "filing_year_to");
  if (filingYearTo !== undefined) query.filing_year_to = filingYearTo;

  const countries = readListParam(params, "country");
  if (countries.length > 0) query.country = countries;

  const assignee = readTextParam(params, "assignee");
  if (assignee) query.assignee = assignee;
  const keyword = readTextParam(params, "keyword");
  if (keyword) query.keyword = keyword;
  const applicationArea = readTextParam(params, "application_area");
  if (applicationArea) query.application_area = applicationArea;
  const classification = readTextParam(params, "classification");
  if (classification) query.classification = classification;

  return query;
}

// Applied patent-filter query -> URL params, preserving any non-filter params
// already present (e.g. the Map view's `focus` deep-link or the top-bar `q`
// search term). Reuses compactParams so the encoding matches exactly what the
// /api/landscape and /api/analytics endpoints receive.
function writeFiltersToParams(
  previous: URLSearchParams,
  query: LandscapeQuery,
): URLSearchParams {
  const next = new URLSearchParams(previous);
  for (const key of PATENT_FILTER_KEYS) next.delete(key);

  const compacted = compactParams({
    source: query.source,
    publication_year_from: query.publication_year_from,
    publication_year_to: query.publication_year_to,
    filing_year_from: query.filing_year_from,
    filing_year_to: query.filing_year_to,
    country: query.country,
    assignee: query.assignee,
    keyword: query.keyword,
    application_area: query.application_area,
    classification: query.classification,
  });

  for (const [key, value] of Object.entries(compacted)) {
    if (Array.isArray(value)) {
      for (const item of value) next.append(key, String(item));
    } else {
      next.set(key, String(value));
    }
  }
  return next;
}

// App-level filter state is mounted inside the router so Overview, Map, and
// Trends share one URL-backed context.
export function FilterProvider({ children }: { children: ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const search = searchParams.toString();

  // Re-derive only when the query string actually changes, so the exposed
  // objects keep stable identities across unrelated re-renders. That keeps them
  // safe to use directly in react-query keys and effect dependency arrays.
  const filters = useMemo(
    () => parseFiltersFromParams(new URLSearchParams(search)),
    [search],
  );
  const form = useMemo(() => landscapeFormFromQuery(filters), [filters]);
  const hasActiveFilters = useMemo(
    () => Object.keys(filters).length > 0,
    [filters],
  );
  const filterSearch = useMemo(
    () => writeFiltersToParams(new URLSearchParams(), filters).toString(),
    [filters],
  );

  const setFilters = useCallback(
    (query: LandscapeQuery) => {
      setSearchParams((previous) => writeFiltersToParams(previous, query));
    },
    [setSearchParams],
  );

  const resetFilters = useCallback(() => {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      for (const key of PATENT_FILTER_KEYS) next.delete(key);
      return next;
    });
  }, [setSearchParams]);

  const value = useMemo<FilterContextValue>(
    () => ({
      filters,
      form,
      activeFilters: filters,
      hasActiveFilters,
      filterSearch,
      setFilters,
      resetFilters,
    }),
    [filters, form, hasActiveFilters, filterSearch, setFilters, resetFilters],
  );

  return (
    <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
  );
}

export function useFilters(): FilterContextValue {
  const context = useContext(FilterContext);
  if (context === null) {
    throw new Error("useFilters must be used within a FilterProvider");
  }
  return context;
}
