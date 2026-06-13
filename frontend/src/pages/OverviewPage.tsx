import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import { getAnalytics } from "../api/analytics";
import { compactParams, getLandscape } from "../api/landscape";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { MetricCard, type MetricVariant } from "../components/common/MetricCard";
import { PageHeader } from "../components/common/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { BarChart, ChartCard, LineChart } from "../components/charts";
import type { ChartTableData } from "../components/charts";
import {
  barToTable,
  isEmptyMap,
  toBar,
} from "../components/charts/analyticsTransforms";
import {
  LandscapeMiniGraph,
  colorForGroup,
} from "../components/landscape/LandscapeMiniGraph";
import {
  buildActiveFilterChips,
  formatInteger,
} from "../components/filters/patentFilterModel";
import { buildOverviewWhiteSpace } from "../components/opportunity/buildOverviewWhiteSpace";
import { useFilters } from "../state/FilterProvider";
import type { AnalyticsResponse } from "../types/analytics";
import type {
  LandscapeNode,
  LandscapeQuery,
  LandscapeResponse,
} from "../types/landscape";

// Overview drill-downs target Map and Trends while carrying shared filters.
const MAP_ROUTE = "/map";
const TRENDS_ROUTE = "/analytics";

// A light edge cap keeps the Overview density thumbnail cheap to fetch; the full
// interactive map (with all relationships) lives on the Map route.
const THUMBNAIL_MAX_EDGES = 160;

// Encode an applied patent-filter query as a bare query string using the same
// compaction as the API. Drill-downs can carry the active filter and optionally
// add one facet.
function searchForQuery(query: LandscapeQuery): string {
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
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(compacted)) {
    if (Array.isArray(value)) {
      for (const item of value) params.append(key, String(item));
    } else {
      params.set(key, String(value));
    }
  }
  return params.toString();
}

function countDistinctAssignees(nodes: LandscapeNode[]): number {
  const seen = new Set<string>();
  for (const node of nodes) {
    const assignee = (node.assignee ?? "").trim();
    if (assignee) seen.add(assignee);
  }
  return seen.size;
}

function yearSpanLabel(byYear: Record<string, number>): string | null {
  const years = Object.keys(byYear)
    .map((year) => Number(year))
    .filter((year) => Number.isFinite(year));
  if (years.length === 0) return null;
  const min = Math.min(...years);
  const max = Math.max(...years);
  return min === max ? String(min) : `${min}–${max}`;
}

export function OverviewPage() {
  // Overview reads the URL-backed shared filter so its tiles, charts, and
  // "Showing X of Y" reflect the same slice as Map and Trends,
  // and drill-downs carry that filter onward. It does not host the editable
  // filter panel — refining the filter happens on Map/Trends.
  const { filters, activeFilters, hasActiveFilters, filterSearch, resetFilters } =
    useFilters();

  // Shares the analytics query key with Trends, so a filter applied on either
  // view warms the other's cache. keepPreviousData keeps tiles/charts visible
  // (not flashing to a spinner) while a new filter result is fetched.
  const analyticsQuery = useQuery({
    queryKey: ["analytics", filters],
    queryFn: ({ signal }) => getAnalytics(filters, signal),
    placeholderData: keepPreviousData,
  });

  // Cluster count, distinct-assignee count, and the density thumbnail all come
  // from one filter-aware landscape fetch.
  const landscapeQuery = useQuery({
    queryKey: ["overview", "landscape", filters],
    queryFn: ({ signal }) =>
      getLandscape({ ...filters, max_edges: THUMBNAIL_MAX_EDGES }, signal),
    placeholderData: keepPreviousData,
  });

  const data = analyticsQuery.data;

  if (analyticsQuery.isPending && !data) {
    return (
      <section>
        <OverviewHeader />
        <LoadingState message="Loading the overview..." />
      </section>
    );
  }

  if ((analyticsQuery.isError || !data) && !data) {
    const error = analyticsQuery.error;
    return (
      <section>
        <OverviewHeader />
        <ErrorState
          message={
            error instanceof ApiError
              ? error.detail
              : error
              ? String(error)
              : "Unknown error"
          }
          hint="Make sure the FastAPI backend is running at the configured VITE_API_BASE_URL."
        />
      </section>
    );
  }

  return (
    <section className="overview-page">
      <OverviewHeader />

      <OverviewBody
        data={data}
        landscape={landscapeQuery.data}
        landscapeIsError={landscapeQuery.isError}
        filters={filters}
        filterSearch={filterSearch}
        hasActiveFilters={hasActiveFilters}
        activeFilterChips={buildActiveFilterChips(activeFilters)}
        isFetching={analyticsQuery.isFetching || landscapeQuery.isFetching}
        onResetFilters={resetFilters}
      />
    </section>
  );
}

function OverviewHeader() {
  return (
    <PageHeader
      eyebrow="Overview"
      title="Patent landscape at a glance"
      description="Loaded corpus snapshot: patents, players, growth, and gaps."
    />
  );
}

interface OverviewBodyProps {
  data: AnalyticsResponse;
  landscape: LandscapeResponse | undefined;
  landscapeIsError: boolean;
  filters: LandscapeQuery;
  filterSearch: string;
  hasActiveFilters: boolean;
  activeFilterChips: Array<{ key: string; label: string }>;
  isFetching: boolean;
  onResetFilters: () => void;
}

function OverviewBody({
  data,
  landscape,
  landscapeIsError,
  filters,
  filterSearch,
  hasActiveFilters,
  activeFilterChips,
  isFetching,
  onResetFilters,
}: OverviewBodyProps) {
  const totalAfter = data.total_records_after_filter;
  const totalBefore = data.total_records_before_filter;

  const clusterCount = landscape?.technology_group_count;
  const assigneeCount = landscape
    ? countDistinctAssignees(landscape.nodes)
    : undefined;
  const span = yearSpanLabel(data.trends.by_publication_year);

  return (
    <>
      <div className="overview-summary result-summary" aria-live="polite">
        <span>
          Showing <strong>{formatInteger(totalAfter)}</strong> of{" "}
          <strong>{formatInteger(totalBefore)}</strong> patents
          {hasActiveFilters ? " for the active filter" : ""}.
        </span>
        <span className="overview-summary__filters">
          {hasActiveFilters ? (
            <>
              {activeFilterChips.map((chip) => (
                <span key={chip.key} className="chip chip--keyword">
                  {chip.label}
                </span>
              ))}
              <button
                type="button"
                className="button button--ghost button--sm"
                onClick={onResetFilters}
              >
                Reset filter
              </button>
            </>
          ) : (
            <Link className="overview-doorway" to={{ pathname: MAP_ROUTE, search: filterSearch }}>
              Refine on the Map →
            </Link>
          )}
          {isFetching && (
            <span className="result-summary__hint">
              <span className="loading-state__spinner" aria-hidden="true" />
              Updating…
            </span>
          )}
        </span>
      </div>

      <div className="metric-grid">
        <HeroTile
          to={MAP_ROUTE}
          search={filterSearch}
          label="Corpus size"
          value={formatInteger(totalAfter)}
          hint={
            hasActiveFilters
              ? `of ${formatInteger(totalBefore)} loaded · open the Map →`
              : "patents in view · open the Map →"
          }
          variant="primary"
        />
        <HeroTile
          to={TRENDS_ROUTE}
          search={filterSearch}
          label="Active assignees"
          value={assigneeCount !== undefined ? formatInteger(assigneeCount) : "—"}
          hint="organizations in view · open Trends →"
        />
        <HeroTile
          to={TRENDS_ROUTE}
          search={filterSearch}
          label="Year span"
          value={span ?? "—"}
          hint="publication years in view · open Trends →"
        />
        <HeroTile
          to={MAP_ROUTE}
          search={filterSearch}
          label="Technology clusters"
          value={clusterCount !== undefined ? formatInteger(clusterCount) : "—"}
          hint="grouped on the Map · open the Map →"
          variant="accent"
        />
      </div>

      <div className="analytics-grid">
        <WhatsGrowingCard data={data} filterSearch={filterSearch} />
        <TopPlayersCard data={data} filterSearch={filterSearch} />
        <TopAreasCard data={data} filterSearch={filterSearch} />
        <DensityThumbnailCard
          landscape={landscape}
          landscapeIsError={landscapeIsError}
          filterSearch={filterSearch}
        />
      </div>

      <WhiteSpaceSection data={data} filters={filters} filterSearch={filterSearch} />
    </>
  );
}

interface HeroTileProps {
  to: string;
  search: string;
  label: string;
  value: string;
  hint: string;
  variant?: MetricVariant;
}

function HeroTile({ to, search, label, value, hint, variant }: HeroTileProps) {
  return (
    <Link
      className="overview-tile-link"
      to={{ pathname: to, search }}
      aria-label={`${label}: ${value}. ${hint}`}
    >
      <MetricCard label={label} value={value} hint={hint} variant={variant} />
    </Link>
  );
}

function DoorwayLink({
  to,
  search,
  children,
}: {
  to: string;
  search: string;
  children: React.ReactNode;
}) {
  return (
    <Link className="overview-doorway" to={{ pathname: to, search }}>
      {children}
    </Link>
  );
}

function WhatsGrowingCard({
  data,
  filterSearch,
}: {
  data: AnalyticsResponse;
  filterSearch: string;
}) {
  const publication = toBar(data.trends.by_publication_year);
  const noResults = data.total_records_after_filter === 0;
  const table: ChartTableData = barToTable(
    "Patents by publication year",
    ["Publication year", "Patents"],
    publication,
  );
  return (
    <ChartCard
      title="What's growing"
      description="Publication volume over time in the current view."
      className="analytics-grid__wide"
      isEmpty={isEmptyMap(data.trends.by_publication_year)}
      emptyMessage={
        noResults
          ? "No patents match the active filter — widen it to see the trend."
          : "No publication-year data is available for these records."
      }
      table={table}
      actions={
        <DoorwayLink to={TRENDS_ROUTE} search={filterSearch}>
          Open in Trends →
        </DoorwayLink>
      }
    >
      <LineChart
        categories={publication.categories}
        series={[{ name: "Publications", data: publication.values }]}
        area
        ariaLabel="Patents by publication year"
      />
    </ChartCard>
  );
}

function TopPlayersCard({
  data,
  filterSearch,
}: {
  data: AnalyticsResponse;
  filterSearch: string;
}) {
  const top = toBar(data.assignees.top, 8);
  const table: ChartTableData = barToTable(
    "Top assignees by patent count",
    ["Assignee", "Patents"],
    top,
  );
  return (
    <ChartCard
      title="Top players"
      description="Organizations with the most patents in view."
      isEmpty={isEmptyMap(data.assignees.top)}
      emptyMessage="No assignee data for these records — many carry no recognized organization."
      table={table}
      actions={
        <DoorwayLink to={TRENDS_ROUTE} search={filterSearch}>
          Open in Trends →
        </DoorwayLink>
      }
    >
      <BarChart
        categories={top.categories}
        values={top.values}
        horizontal
        height={340}
        ariaLabel="Top assignees by patent count"
      />
    </ChartCard>
  );
}

function TopAreasCard({
  data,
  filterSearch,
}: {
  data: AnalyticsResponse;
  filterSearch: string;
}) {
  const areas = toBar(data.technology.application_areas, 8);
  const table: ChartTableData = barToTable(
    "Top candidate application areas",
    ["Application area", "Patents"],
    areas,
  );
  return (
      <ChartCard
        title="Top application areas"
      description="Candidate application areas by patent count."
      isEmpty={isEmptyMap(data.technology.application_areas)}
      emptyMessage="No candidate application areas for these records."
      table={table}
      actions={
        <DoorwayLink to={MAP_ROUTE} search={filterSearch}>
          Explore on the Map →
        </DoorwayLink>
      }
    >
      <BarChart
        categories={areas.categories}
        values={areas.values}
        horizontal
        color="#0f766e"
        height={340}
        ariaLabel="Top candidate application areas"
      />
    </ChartCard>
  );
}

function DensityThumbnailCard({
  landscape,
  landscapeIsError,
  filterSearch,
}: {
  landscape: LandscapeResponse | undefined;
  landscapeIsError: boolean;
  filterSearch: string;
}) {
  const groups = landscape
    ? [...landscape.technology_groups].sort(
        (a, b) => b.patent_count - a.patent_count,
      )
    : [];
  const isEmpty =
    landscapeIsError || !landscape || landscape.node_count === 0;

  return (
      <ChartCard
        title="Technology clusters & density"
      description="Text-similarity cluster density."
      className="analytics-grid__wide"
      isEmpty={isEmpty}
      emptyMessage={
        landscapeIsError
          ? "The relationship map could not be loaded. The rest of the overview is unaffected."
          : "No patents match the active filter, so no clusters were formed."
      }
      actions={
        <DoorwayLink to={MAP_ROUTE} search={filterSearch}>
          Open the Map →
        </DoorwayLink>
      }
    >
      {landscape && (
        <div className="overview-density">
          <LandscapeMiniGraph
            data={landscape}
            interactive={false}
            height={300}
            caption={null}
            ariaLabel="Technology cluster density preview"
          />
          {groups.length > 0 && (
            <ul className="overview-clusters" aria-label="Technology clusters by size">
              {groups.slice(0, 8).map((group) => (
                <li key={group.technology_group_id} className="overview-clusters__item">
                  <span
                    className="overview-clusters__swatch"
                    style={{ background: colorForGroup(group.technology_group_id) }}
                    aria-hidden="true"
                  />
                  <span className="overview-clusters__label">
                    {group.group_label || group.technology_group}
                  </span>
                  <span className="overview-clusters__count">
                    {formatInteger(group.patent_count)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </ChartCard>
  );
}

function WhiteSpaceSection({
  data,
  filters,
  filterSearch,
}: {
  data: AnalyticsResponse;
  filters: LandscapeQuery;
  filterSearch: string;
}) {
  const whiteSpace = buildOverviewWhiteSpace(data);
  const recentNote =
    whiteSpace.recentShare !== null && whiteSpace.recentWindow !== null
      ? `${Math.round(whiteSpace.recentShare * 100)}% of records are from ${whiteSpace.recentWindow.from}–${whiteSpace.recentWindow.to}; thin areas may be early.`
      : null;

  return (
    <SectionCard
      title="Underexplored areas (white space)"
      description="Exploratory signal, not a market or legal guarantee."
      actions={
        <DoorwayLink to={MAP_ROUTE} search={filterSearch}>
          Explore the Map →
        </DoorwayLink>
      }
    >
      {whiteSpace.areas.length === 0 ? (
        <p className="card__muted">
          {whiteSpace.totalAreas === 0
            ? "No candidate application areas are available for these records."
            : "No clearly underexplored application areas for the active filter."}
        </p>
      ) : (
        <>
          <p className="overview-whitespace__context">
            Median area: {whiteSpace.medianCount.toFixed(1)} records. Largest:
            {" "}
            {formatInteger(whiteSpace.maxCount)}.
            {recentNote ? ` ${recentNote}` : ""}
          </p>
          <ul className="overview-whitespace__grid">
            {whiteSpace.areas.map((area) => (
              <li key={area.name}>
                <Link
                  className="overview-whitespace__card"
                  to={{
                    pathname: MAP_ROUTE,
                    search: searchForQuery({
                      ...filters,
                      application_area: area.name,
                    }),
                  }}
                  aria-label={`Explore ${area.name} on the Map — ${area.count} ${
                    area.count === 1 ? "record" : "records"
                  } in view`}
                >
                  <span className="overview-whitespace__name">{area.name}</span>
                  <span className="overview-whitespace__meta">
                    <span className="overview-whitespace__count">
                      {formatInteger(area.count)}{" "}
                      {area.count === 1 ? "record" : "records"}
                    </span>
                    <span className="overview-whitespace__go" aria-hidden="true">
                      Explore on the Map →
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </SectionCard>
  );
}
