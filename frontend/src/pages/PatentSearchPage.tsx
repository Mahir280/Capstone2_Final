import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import {
  getFilterOptions,
  getPatents,
  searchPatents,
} from "../api/patents";
import { Badge } from "../components/common/Badge";
import { DatasetWarningCallout } from "../components/common/DatasetWarningCallout";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { PageHeader } from "../components/common/PageHeader";
import { PatentCard } from "../components/patents/PatentCard";
import {
  ALL_FILTER_VALUE,
  isFilterActive,
  type PatentSearchParams,
  type PatentSearchResponse,
} from "../types/patents";

const LIMIT_OPTIONS = [10, 20, 50] as const;
const SEARCH_DEBOUNCE_MS = 300;

interface FormState {
  q: string;
  source: string;
  assignee: string;
  country: string;
  year: string;
  limit: number;
}

const INITIAL_FORM: FormState = {
  q: "",
  source: ALL_FILTER_VALUE,
  assignee: ALL_FILTER_VALUE,
  country: ALL_FILTER_VALUE,
  year: ALL_FILTER_VALUE,
  limit: LIMIT_OPTIONS[0],
};

export function PatentSearchPage() {
  // Seed the query from the `q` URL param so the persistent top-bar search box
  // (Topbar) reaches this workflow with the typed term applied.
  const [urlSearchParams] = useSearchParams();
  const urlQuery = urlSearchParams.get("q") ?? "";

  const [form, setForm] = useState<FormState>(() => ({
    ...INITIAL_FORM,
    q: urlQuery,
  }));
  const [appliedQuery, setAppliedQuery] = useState<string>(urlQuery);
  const [offset, setOffset] = useState<number>(0);

  // Re-seed when the top-bar search navigates here with a new `q` value.
  useEffect(() => {
    setForm((prev) => (prev.q === urlQuery ? prev : { ...prev, q: urlQuery }));
    setAppliedQuery(urlQuery);
    setOffset(0);
  }, [urlQuery]);

  useEffect(() => {
    if (form.q === appliedQuery) return;
    const handle = window.setTimeout(() => {
      setAppliedQuery(form.q);
      setOffset(0);
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [form.q, appliedQuery]);

  useEffect(() => {
    setOffset(0);
  }, [form.source, form.assignee, form.country, form.year, form.limit]);

  const filterOptionsQuery = useQuery({
    queryKey: ["filter-options"],
    queryFn: ({ signal }) => getFilterOptions(signal),
    staleTime: 5 * 60_000,
  });

  const searchParams: PatentSearchParams = useMemo(
    () => ({
      q: appliedQuery,
      source: form.source,
      assignee: form.assignee,
      country: form.country,
      year: form.year,
      limit: form.limit,
      offset,
    }),
    [
      appliedQuery,
      form.source,
      form.assignee,
      form.country,
      form.year,
      form.limit,
      offset,
    ],
  );

  const filtersActive = isFilterActive(searchParams);

  const patentsQuery = useQuery<PatentSearchResponse, Error>({
    queryKey: ["patents", searchParams],
    queryFn: ({ signal }) =>
      filtersActive
        ? searchPatents(searchParams, signal)
        : getPatents({ limit: form.limit, offset }, signal),
    placeholderData: keepPreviousData,
  });

  const handleClearFilters = () => {
    setForm(INITIAL_FORM);
    setAppliedQuery("");
    setOffset(0);
  };

  const formIsDefault =
    form.q === "" &&
    form.source === ALL_FILTER_VALUE &&
    form.assignee === ALL_FILTER_VALUE &&
    form.country === ALL_FILTER_VALUE &&
    form.year === ALL_FILTER_VALUE &&
    form.limit === INITIAL_FORM.limit;

  const data = patentsQuery.data;
  const total = data?.total_results ?? 0;
  const returned = data?.returned_results ?? 0;
  const rangeStart = data && returned > 0 ? offset + 1 : 0;
  const rangeEnd = data ? offset + returned : 0;
  const canPrev = offset > 0;
  const canNext = data ? offset + returned < total : false;

  return (
    <section>
      <PageHeader
        eyebrow="Explore"
        title="Search"
        description="Search the current corpus and open patent dossiers."
        meta={
          <>
            <Badge variant="primary" withDot>
              Optimized grouping support
            </Badge>
            <Badge variant="neutral">Decision-support reading aid</Badge>
          </>
        }
      />

      <form
        className="search-hero"
        role="search"
        aria-label="Search and exploration filters"
        onSubmit={(event) => {
          event.preventDefault();
          setAppliedQuery(form.q);
          setOffset(0);
        }}
      >
        <div className="search-hero__input-row">
          <div className="search-hero__input-wrap">
            <svg
              className="search-hero__icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <input
              className="search-hero__input"
              type="search"
              value={form.q}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, q: event.target.value }))
              }
              placeholder="Search title, abstract, organization, or keyword…"
              autoComplete="off"
              aria-label="Search query"
            />
          </div>
          <button type="submit" className="button button--lg">
            Search
          </button>
        </div>

        <div className="filter-bar__row">
          <label className="filter-field">
            <span className="filter-field__label">Source authority</span>
            <select
              value={form.source}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, source: event.target.value }))
              }
            >
              <option value={ALL_FILTER_VALUE}>All</option>
              {filterOptionsQuery.data?.sources.map((source) => (
                <option key={source} value={source}>
                  {source}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span className="filter-field__label">Country</span>
            <select
              value={form.country}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, country: event.target.value }))
              }
            >
              <option value={ALL_FILTER_VALUE}>All</option>
              {filterOptionsQuery.data?.countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span className="filter-field__label">Year</span>
            <select
              value={form.year}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, year: event.target.value }))
              }
            >
              <option value={ALL_FILTER_VALUE}>All</option>
              {filterOptionsQuery.data?.years.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span className="filter-field__label">Assignee</span>
            <select
              value={form.assignee}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, assignee: event.target.value }))
              }
            >
              <option value={ALL_FILTER_VALUE}>All</option>
              {filterOptionsQuery.data?.assignees.map((assignee) => (
                <option key={assignee} value={assignee}>
                  {assignee}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span className="filter-field__label">Per page</span>
            <select
              value={form.limit}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  limit: Number(event.target.value),
                }))
              }
            >
              {LIMIT_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="filter-bar__actions">
          <span className="filter-bar__hint">
            {filtersActive
              ? "Filters active."
              : "Browsing full corpus."}
          </span>
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={handleClearFilters}
            disabled={formIsDefault}
          >
            Clear all
          </button>
        </div>
      </form>

      {patentsQuery.isPending && !data && (
        <LoadingState message="Loading patents..." />
      )}

      {patentsQuery.isError && (
        <ErrorState
          message={
            patentsQuery.error instanceof ApiError
              ? patentsQuery.error.detail
              : String(patentsQuery.error)
          }
          hint="Make sure the FastAPI backend is running at the configured VITE_API_BASE_URL."
        />
      )}

      {data && <DatasetWarningCallout warnings={data.warnings} />}

      {data && (
        <div className="result-summary" aria-live="polite">
          {total > 0 ? (
            <span>
              Showing <strong>{rangeStart}</strong>–<strong>{rangeEnd}</strong>{" "}
              of <strong>{total}</strong> corpus records
              {filtersActive ? " for the active filters" : ""}.
            </span>
          ) : (
            <span>No matching patents.</span>
          )}
          {patentsQuery.isFetching && (
            <span className="result-summary__hint">
              <span className="loading-state__spinner" aria-hidden="true" />
              Updating…
            </span>
          )}
        </div>
      )}

      {data && data.patents.length === 0 && !patentsQuery.isError && (
        <EmptyState
          title={filtersActive ? "No matches" : "Dataset is empty"}
          message={
            filtersActive
              ? "No patents match these filters. Try widening the search or clearing filters."
              : "No patents are available yet. Load a curated corpus from Corpus & Sources."
          }
        />
      )}

      {data?.patents.map((patent) => (
        <PatentCard key={patent.analysis_id} patent={patent} />
      ))}

      {data && total > form.limit && (
        <div className="pagination">
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={() => setOffset((prev) => Math.max(0, prev - form.limit))}
            disabled={!canPrev || patentsQuery.isFetching}
          >
            ← Previous
          </button>
          <span className="pagination__page">
            Page {Math.floor(offset / form.limit) + 1} of{" "}
            {Math.max(1, Math.ceil(total / form.limit))}
          </span>
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={() => setOffset((prev) => prev + form.limit)}
            disabled={!canNext || patentsQuery.isFetching}
          >
            Next →
          </button>
        </div>
      )}
    </section>
  );
}
