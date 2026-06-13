import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import { getAnalytics } from "../api/analytics";
import { getLandscape, getLandscapeFilterOptions } from "../api/landscape";
import { Callout } from "../components/common/Callout";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { MetricCard } from "../components/common/MetricCard";
import { PageHeader } from "../components/common/PageHeader";
import {
  BarChart,
  ChartCard,
  HeatmapChart,
  HistogramChart,
  LineChart,
  PieChart,
  StackedBarChart,
  colorForSource,
} from "../components/charts";
import {
  barToTable,
  buildHistogram,
  crossTabToHeatmap,
  crossTabToStacked,
  isEmptyCrossTab,
  isEmptyMap,
  toBar,
} from "../components/charts/analyticsTransforms";
import type { ChartTableData } from "../components/charts";
import { CorpusHealthCard } from "../components/insights/CorpusHealthCard";
import { PatentFilterPanel } from "../components/filters/PatentFilterPanel";
import {
  EMPTY_LANDSCAPE_FILTER_FORM,
  buildLandscapeQueryFromForm,
  formatInteger,
  type LandscapeFilterFormState,
} from "../components/filters/patentFilterModel";
import { useFilters } from "../state/FilterProvider";
import type { AnalyticsResponse } from "../types/analytics";
import type {
  LandscapeActiveFilters,
  LandscapeNode,
  LandscapeResponse,
} from "../types/landscape";

const MAP_MAX_EDGES = 500;

type AnalyticsTab =
  | "corpus"
  | "trends"
  | "assignees"
  | "technology"
  | "map"
  | "quality";

const TABS: Array<{ id: AnalyticsTab; label: string }> = [
  { id: "corpus", label: "Corpus" },
  { id: "trends", label: "Trends" },
  { id: "assignees", label: "Assignees" },
  { id: "technology", label: "Technology" },
  { id: "map", label: "Map Metrics" },
  { id: "quality", label: "Data Quality" },
];

const QUALITY_FIELD_LABELS: Record<string, string> = {
  assignee: "Assignee",
  country: "Country",
  publication_date: "Publication date",
  filing_date: "Filing date",
  abstract: "Abstract",
  keywords: "Keywords",
  ipc_codes: "IPC codes",
  cpc_codes: "CPC codes",
  application_areas: "Application areas",
};

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

// Percentage of in-view records that populate a given field, from the quality
// aggregates. Used to phrase sparse-data notes with real numbers.
function completenessPct(
  data: AnalyticsResponse,
  field: string,
): number | undefined {
  const value = data.quality.field_completeness_pct[field];
  return typeof value === "number" ? value : undefined;
}

// Below this share of in-view records, a metadata-backed chart gets a note
// explaining it only covers a subset.
const SPARSE_COVERAGE_THRESHOLD = 60;

export function VisualAnalyticsPage() {
  // The applied patent filters are shared app-wide (URL-backed) via FilterProvider
  // so a filter set on Map carries into Trends (and vice versa), is shareable, and
  // survives reload. The active analytics tab stays local to this view.
  const {
    filters: appliedFilters,
    form: appliedFilterForm,
    setFilters: setSharedFilters,
    resetFilters: resetSharedFilters,
  } = useFilters();
  const [filterForm, setFilterForm] = useState<LandscapeFilterFormState>(
    () => appliedFilterForm,
  );
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("corpus");

  // Re-seed the local editing buffer whenever the shared applied filters change
  // (arriving from Map, a shared link, reload, or back/forward). Local typing
  // does not change the applied filters, so unapplied edits survive until Apply.
  const appliedFilterFormKey = JSON.stringify(appliedFilterForm);
  useEffect(() => {
    setFilterForm(appliedFilterForm);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appliedFilterFormKey]);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  // Roving-tabindex keyboard support for the tablist (WAI-ARIA tabs pattern):
  // arrow keys move between tabs (wrapping), Home/End jump to the ends.
  const onTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next = index;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      next = (index + 1) % TABS.length;
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      next = (index - 1 + TABS.length) % TABS.length;
    } else if (event.key === "Home") {
      next = 0;
    } else if (event.key === "End") {
      next = TABS.length - 1;
    } else {
      return;
    }
    event.preventDefault();
    setActiveTab(TABS[next].id);
    tabRefs.current[next]?.focus();
  };

  const filterOptionsQuery = useQuery({
    queryKey: ["analytics", "filter-options"],
    queryFn: ({ signal }) => getLandscapeFilterOptions(signal),
  });

  const analyticsQuery = useQuery({
    queryKey: ["analytics", appliedFilters],
    queryFn: ({ signal }) => getAnalytics(appliedFilters, signal),
    placeholderData: keepPreviousData,
  });

  const mapQuery = useQuery({
    queryKey: ["analytics", "map", appliedFilters],
    queryFn: ({ signal }) =>
      getLandscape({ ...appliedFilters, max_edges: MAP_MAX_EDGES }, signal),
    enabled: activeTab === "map",
    placeholderData: keepPreviousData,
  });

  const applyFilters = () => {
    setSharedFilters(buildLandscapeQueryFromForm(filterForm));
  };

  const resetFilters = () => {
    setFilterForm({ ...EMPTY_LANDSCAPE_FILTER_FORM, sources: [] });
    resetSharedFilters();
  };

  const data = analyticsQuery.data;
  const activeFilters: LandscapeActiveFilters = data?.active_filters ?? {};

  if (analyticsQuery.isPending && !data) {
    return (
      <section>
        <AnalyticsHeader />
        <LoadingState message="Loading visual analytics..." />
      </section>
    );
  }

  if ((analyticsQuery.isError || !data) && !data) {
    const err = analyticsQuery.error;
    return (
      <section>
        <AnalyticsHeader />
        <ErrorState
          message={
            err instanceof ApiError
              ? err.detail
              : err
              ? String(err)
              : "Unknown error"
          }
          hint="Make sure the FastAPI backend is running at the configured VITE_API_BASE_URL."
        />
      </section>
    );
  }

  const totalBefore = data.total_records_before_filter;
  const totalAfter = data.total_records_after_filter;

  return (
    <section className="analytics-page">
      <AnalyticsHeader />

      {data.warnings.length > 0 && (
        <Callout variant="info" title="Analytics notes">
          <ul className="analytics-warning-list">
            {data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </Callout>
      )}

      <PatentFilterPanel
        form={filterForm}
        metadata={filterOptionsQuery.data}
        metadataError={filterOptionsQuery.error}
        metadataIsLoading={filterOptionsQuery.isLoading}
        activeFilters={activeFilters}
        filteredCount={totalAfter}
        totalCount={totalBefore}
        isFetching={analyticsQuery.isFetching}
        onChange={setFilterForm}
        onApply={applyFilters}
        onReset={resetFilters}
      />

      <div
        className="analytics-tabs"
        role="tablist"
        aria-label="Analytics sections"
      >
        {TABS.map((tab, index) => (
          <button
            key={tab.id}
            ref={(element) => {
              tabRefs.current[index] = element;
            }}
            type="button"
            role="tab"
            id={`analytics-tab-${tab.id}`}
            aria-selected={tab.id === activeTab}
            aria-controls={`analytics-panel-${tab.id}`}
            tabIndex={tab.id === activeTab ? 0 : -1}
            className={
              tab.id === activeTab
                ? "analytics-tab analytics-tab--active"
                : "analytics-tab"
            }
            onClick={() => setActiveTab(tab.id)}
            onKeyDown={(event) => onTabKeyDown(event, index)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        className="analytics-tab-panel"
        role="tabpanel"
        id={`analytics-panel-${activeTab}`}
        aria-labelledby={`analytics-tab-${activeTab}`}
        tabIndex={0}
      >
        {activeTab === "corpus" && <CorpusTab data={data} />}
        {activeTab === "trends" && <TrendsTab data={data} />}
        {activeTab === "assignees" && <AssigneesTab data={data} />}
        {activeTab === "technology" && <TechnologyTab data={data} />}
        {activeTab === "map" && (
          <MapMetricsTab
            data={mapQuery.data}
            isPending={mapQuery.isPending}
            isError={mapQuery.isError}
            error={mapQuery.error}
          />
        )}
        {activeTab === "quality" && <DataQualityTab data={data} />}
      </div>
    </section>
  );
}

function AnalyticsHeader() {
  return (
    <PageHeader
      eyebrow="Analyze"
      title="Visual analytics"
      description="Filter-aware charts for corpus, trends, players, technology, map metrics, and data quality."
    />
  );
}

function CorpusTab({ data }: { data: AnalyticsResponse }) {
  const bySource = data.corpus.by_source;
  const sourcePie = Object.entries(bySource).map(([name, value]) => ({
    name,
    value,
    color: colorForSource(name),
  }));
  const countryBar = toBar(data.corpus.by_country, 12);
  const sourceCountry = crossTabToStacked(data.corpus.source_country, {
    axis: "inner",
    categoryLimit: 12,
    colorFor: colorForSource,
  });
  const sourceTable: ChartTableData = barToTable(
    "Patents by source authority",
    ["Source authority", "Patents"],
    toBar(bySource),
  );

  return (
    <div className="analytics-grid">
      <ChartCard
        title="Patents by source authority"
        description="Filtered corpus by source authority."
        isEmpty={isEmptyMap(bySource)}
        table={sourceTable}
      >
        <PieChart data={sourcePie} ariaLabel="Patents by source authority" />
      </ChartCard>

      <ChartCard
        title="Top countries"
        description="Most represented countries."
        isEmpty={isEmptyMap(data.corpus.by_country)}
      >
        <BarChart
          categories={countryBar.categories}
          values={countryBar.values}
          horizontal
          ariaLabel="Top countries by patent count"
        />
      </ChartCard>

      <ChartCard
        title="Country composition by source"
        description="Country mix by source authority."
        isEmpty={isEmptyCrossTab(data.corpus.source_country)}
        className="analytics-grid__wide"
      >
        <StackedBarChart
          categories={sourceCountry.categories}
          series={sourceCountry.series}
          ariaLabel="Country composition by source authority"
        />
      </ChartCard>
    </div>
  );
}

function TrendsTab({ data }: { data: AnalyticsResponse }) {
  const noResults = data.total_records_after_filter === 0;
  const publication = toBar(data.trends.by_publication_year);
  const filing = toBar(data.trends.by_filing_year);
  const sourceByYear = crossTabToStacked(data.trends.source_by_year, {
    axis: "outer",
    colorFor: colorForSource,
  });
  const publicationTable: ChartTableData = barToTable(
    "Patents by publication year",
    ["Publication year", "Patents"],
    publication,
  );

  // Filing dates are sparse in the recovered corpus. Distinguish "no records
  // after filter" (clean default empty) from "records exist but lack filing
  // dates" (explanatory note), and add a coverage note when only thinly present.
  const filingEmpty = isEmptyMap(data.trends.by_filing_year);
  const filingPct = completenessPct(data, "filing_date");
  const filingEmptyMessage = noResults
    ? undefined
    : "No filing-year data for these records; filing dates are sparse.";
  const filingNote =
    !filingEmpty && filingPct !== undefined && filingPct < SPARSE_COVERAGE_THRESHOLD
      ? `Filing dates are recorded for only ${Math.round(filingPct)}% of records in view, so this trend understates filing activity.`
      : undefined;

  return (
    <div className="analytics-grid">
      <ChartCard
        title="Patents by publication year"
        description="Publication-year distribution."
        isEmpty={isEmptyMap(data.trends.by_publication_year)}
        table={publicationTable}
      >
        <LineChart
          categories={publication.categories}
          series={[{ name: "Publications", data: publication.values }]}
          area
          ariaLabel="Patents by publication year"
        />
      </ChartCard>

      <ChartCard
        title="Patents by filing year"
        description="Filing-year distribution."
        isEmpty={filingEmpty}
        emptyMessage={filingEmptyMessage}
        note={filingNote}
      >
        <LineChart
          categories={filing.categories}
          series={[
            {
              name: "Filings",
              data: filing.values,
              color: "#0f766e",
            },
          ]}
          area
          ariaLabel="Patents by filing year"
        />
      </ChartCard>

      <ChartCard
        title="Source mix over time"
        description="Yearly volume by source authority."
        isEmpty={isEmptyCrossTab(data.trends.source_by_year)}
        className="analytics-grid__wide"
      >
        <StackedBarChart
          categories={sourceByYear.categories}
          series={sourceByYear.series}
          ariaLabel="Source authority mix over time"
        />
      </ChartCard>
    </div>
  );
}

function AssigneesTab({ data }: { data: AnalyticsResponse }) {
  const noResults = data.total_records_after_filter === 0;
  const top = toBar(data.assignees.top, 15);
  const bySource = crossTabToStacked(data.assignees.by_source, {
    axis: "outer",
    categoryLimit: 12,
    colorFor: colorForSource,
  });
  const byArea = crossTabToHeatmap(data.assignees.by_application_area, {
    rowLimit: 12,
    colLimit: 12,
  });
  const topTable: ChartTableData = barToTable(
    "Top assignees by patent count",
    ["Assignee", "Patents"],
    top,
  );

  // Candidate application areas are derived from text similarity and are sparse.
  const areaEmpty = isEmptyCrossTab(data.assignees.by_application_area);
  const areaPct = completenessPct(data, "application_areas");
  const areaEmptyMessage = noResults
    ? undefined
    : "No candidate application areas for these assignees.";
  const areaNote =
    !areaEmpty && areaPct !== undefined && areaPct < SPARSE_COVERAGE_THRESHOLD
      ? `Candidate application areas are derived for only ${Math.round(areaPct)}% of records in view, so this matrix covers a subset.`
      : undefined;

  return (
    <div className="analytics-grid">
      <ChartCard
        title="Top assignees"
        description="Organizations with the most patents."
        isEmpty={isEmptyMap(data.assignees.top)}
        table={topTable}
        className="analytics-grid__wide"
      >
        <BarChart
          categories={top.categories}
          values={top.values}
          horizontal
          height={420}
          ariaLabel="Top assignees by patent count"
        />
      </ChartCard>

      <ChartCard
        title="Assignee mix by source"
        description="Top assignee portfolios by source authority."
        isEmpty={isEmptyCrossTab(data.assignees.by_source)}
      >
        <StackedBarChart
          categories={bySource.categories}
          series={bySource.series}
          horizontal
          height={420}
          ariaLabel="Assignee portfolio by source authority"
        />
      </ChartCard>

      <ChartCard
        title="Assignee × application area"
        description="Top assignees by candidate application area."
        isEmpty={areaEmpty}
        emptyMessage={areaEmptyMessage}
        note={areaNote}
      >
        <HeatmapChart
          xCategories={byArea.xCategories}
          yCategories={byArea.yCategories}
          data={byArea.data}
          height={420}
          ariaLabel="Assignee versus application area heatmap"
        />
      </ChartCard>
    </div>
  );
}

function TechnologyTab({ data }: { data: AnalyticsResponse }) {
  const noResults = data.total_records_after_filter === 0;
  const keywords = toBar(data.technology.top_keywords, 20);
  const areas = toBar(data.technology.application_areas, 15);
  const classifications = toBar(data.technology.classifications, 15);
  const cooccurrence = crossTabToHeatmap(
    data.technology.keyword_application_area,
    { rowLimit: 15, colLimit: 12 },
  );
  const keywordsTable: ChartTableData = barToTable(
    "Top keywords by frequency",
    ["Keyword", "Frequency"],
    keywords,
  );

  // IPC/CPC classification codes are sparse. Use the better-populated of the two
  // completeness figures as an upper bound on records carrying any classification.
  const classEmpty = Object.keys(data.technology.classifications).length === 0;
  const ipcPct = completenessPct(data, "ipc_codes") ?? 0;
  const cpcPct = completenessPct(data, "cpc_codes") ?? 0;
  const classPct = Math.max(ipcPct, cpcPct);
  const classEmptyMessage = noResults
    ? undefined
    : "No IPC/CPC classification codes for these records.";
  const classNote =
    !classEmpty && classPct < SPARSE_COVERAGE_THRESHOLD
      ? `Classification codes are recorded for only ~${Math.round(classPct)}% of records in view, so this distribution covers a subset.`
      : undefined;

  return (
    <div className="analytics-grid">
      <ChartCard
        title="Top keywords"
        description="Most frequent extracted keywords."
        isEmpty={isEmptyMap(data.technology.top_keywords)}
        table={keywordsTable}
        className="analytics-grid__wide"
      >
        <BarChart
          categories={keywords.categories}
          values={keywords.values}
          horizontal
          height={460}
          ariaLabel="Top keywords by frequency"
        />
      </ChartCard>

      <ChartCard
        title="Candidate application areas"
        description="Candidate areas by count."
        isEmpty={isEmptyMap(data.technology.application_areas)}
      >
        <BarChart
          categories={areas.categories}
          values={areas.values}
          horizontal
          color="#0f766e"
          ariaLabel="Candidate application areas"
        />
      </ChartCard>

      <ChartCard
        title="Classification prefixes"
        description="IPC/CPC prefixes in view."
        isEmpty={classEmpty}
        emptyMessage={classEmptyMessage}
        note={classNote}
      >
        <BarChart
          categories={classifications.categories}
          values={classifications.values}
          horizontal
          color="#6366f1"
          ariaLabel="Classification prefixes"
        />
      </ChartCard>

      <ChartCard
        title="Keyword × application area"
        description="Keyword and candidate-area co-occurrence."
        isEmpty={isEmptyCrossTab(data.technology.keyword_application_area)}
        className="analytics-grid__wide"
      >
        <HeatmapChart
          xCategories={cooccurrence.xCategories}
          yCategories={cooccurrence.yCategories}
          data={cooccurrence.data}
          height={460}
          ariaLabel="Keyword versus application area heatmap"
        />
      </ChartCard>
    </div>
  );
}

interface MapMetricsTabProps {
  data: LandscapeResponse | undefined;
  isPending: boolean;
  isError: boolean;
  error: unknown;
}

function MapMetricsTab({ data, isPending, isError, error }: MapMetricsTabProps) {
  const derived = useMemo(() => deriveMapMetrics(data), [data]);

  if (isPending && !data) {
    return <LoadingState message="Loading relationship-map metrics..." />;
  }
  if ((isError || !data) && !data) {
    return (
      <ErrorState
        message={
          error instanceof ApiError
            ? error.detail
            : error
            ? String(error)
            : "Unknown error"
        }
        hint="Relationship-map metrics are derived from the /api/landscape endpoint."
      />
    );
  }
  if (!derived) return null;

  return (
    <div className="analytics-grid">
      <div className="analytics-grid__wide metric-grid">
        <MetricCard
          label="Visible patents"
          value={formatInteger(derived.nodeCount)}
          hint="Nodes in the relationship map"
          variant="primary"
        />
        <MetricCard
          label="Relationships"
          value={formatInteger(derived.edgeCount)}
          hint={`Up to ${MAP_MAX_EDGES} strongest edges`}
          variant="accent"
        />
        <MetricCard
          label="Avg relationships / patent"
          value={derived.averageRelationships.toFixed(2)}
          hint="Mean edges per visible patent"
        />
        <MetricCard
          label="Edge density"
          value={formatPercent(derived.density * 100)}
          hint="Share of all possible pairs that are linked"
        />
      </div>

      <ChartCard
        title="Technology group sizes"
        description="Patents per technology group."
        isEmpty={derived.groupSizes.categories.length === 0}
      >
        <BarChart
          categories={derived.groupSizes.categories}
          values={derived.groupSizes.values}
          horizontal
          ariaLabel="Technology group sizes"
        />
      </ChartCard>

      <ChartCard
        title="Relationship similarity distribution"
        description="Similarity scores across visible relationships."
        isEmpty={derived.similarityBins.length === 0}
      >
        <HistogramChart
          bins={derived.similarityBins}
          valueName="Relationships"
          ariaLabel="Relationship similarity distribution"
        />
      </ChartCard>

      <ChartCard
        title="Strongest relationships"
        description="Highest-similarity patent pairs."
        isEmpty={derived.strongestPairs.length === 0}
        className="analytics-grid__wide"
      >
        <ol className="analytics-pair-list">
          {derived.strongestPairs.map((pair) => (
            <li key={pair.key} className="analytics-pair">
              <span className="analytics-pair__score chip chip--keyword">
                {pair.score.toFixed(3)}
              </span>
              <span className="analytics-pair__titles">
                <span>{pair.sourceTitle}</span>
                <span className="analytics-pair__arrow" aria-hidden="true">
                  ↔
                </span>
                <span>{pair.targetTitle}</span>
              </span>
            </li>
          ))}
        </ol>
      </ChartCard>
    </div>
  );
}

interface StrongestPair {
  key: string;
  score: number;
  sourceTitle: string;
  targetTitle: string;
}

interface MapMetrics {
  nodeCount: number;
  edgeCount: number;
  averageRelationships: number;
  density: number;
  groupSizes: { categories: string[]; values: number[] };
  similarityBins: ReturnType<typeof buildHistogram>;
  strongestPairs: StrongestPair[];
}

function deriveMapMetrics(
  data: LandscapeResponse | undefined,
): MapMetrics | null {
  if (!data) return null;

  const nodeCount = data.node_count;
  const edgeCount = data.edge_count;
  const possiblePairs = nodeCount > 1 ? (nodeCount * (nodeCount - 1)) / 2 : 0;
  const density = possiblePairs > 0 ? edgeCount / possiblePairs : 0;

  const groups = [...data.technology_groups].sort(
    (a, b) => b.patent_count - a.patent_count,
  );
  const groupSizes = {
    categories: groups.map((group) => group.group_label || group.technology_group),
    values: groups.map((group) => group.patent_count),
  };

  const similarityBins = buildHistogram(
    data.edges.map((edge) => edge.similarity_score),
    10,
  );

  const nodeIndex = new Map<string, LandscapeNode>();
  for (const node of data.nodes) nodeIndex.set(node.analysis_id, node);
  const titleFor = (analysisId: string): string => {
    const node = nodeIndex.get(analysisId);
    if (!node) return analysisId;
    return node.title || node.patent_id || analysisId;
  };

  const strongestPairs: StrongestPair[] = [...data.edges]
    .sort((a, b) => b.similarity_score - a.similarity_score)
    .slice(0, 8)
    .map((edge) => ({
      key: `${edge.source_analysis_id}-${edge.target_analysis_id}`,
      score: edge.similarity_score,
      sourceTitle: titleFor(edge.source_analysis_id),
      targetTitle: titleFor(edge.target_analysis_id),
    }));

  return {
    nodeCount,
    edgeCount,
    averageRelationships: data.average_relationships,
    density,
    groupSizes,
    similarityBins,
    strongestPairs,
  };
}

function DataQualityTab({ data }: { data: AnalyticsResponse }) {
  const completeness = data.quality.field_completeness_pct;
  const missing = data.quality.missing_by_field;
  const fieldKeys = Object.keys(completeness);

  const completenessBar = {
    categories: fieldKeys.map((key) => QUALITY_FIELD_LABELS[key] ?? key),
    values: fieldKeys.map((key) => completeness[key]),
  };
  const missingBar = {
    categories: fieldKeys.map((key) => QUALITY_FIELD_LABELS[key] ?? key),
    values: fieldKeys.map((key) => missing[key] ?? 0),
  };
  const completenessTable: ChartTableData = {
    caption: "Field completeness percentage",
    columns: ["Field", "% complete"],
    rows: fieldKeys.map((key) => [
      QUALITY_FIELD_LABELS[key] ?? key,
      formatPercent(completeness[key]),
    ]),
  };
  const missingTable: ChartTableData = {
    caption: "Missing values by field",
    columns: ["Field", "Missing records"],
    rows: fieldKeys.map((key) => [
      QUALITY_FIELD_LABELS[key] ?? key,
      missing[key] ?? 0,
    ]),
  };
  const scorePct = data.quality.completeness_score * 100;
  const scoreVariant =
    scorePct >= 80 ? "success" : scorePct >= 50 ? "warning" : "default";

  return (
    <div className="analytics-grid">
      <CorpusHealthCard data={data} />

      <div className="analytics-grid__wide metric-grid">
        <MetricCard
          label="Overall completeness"
          value={formatPercent(scorePct)}
          hint="Average field presence across tracked fields"
          variant={scoreVariant}
        />
        <MetricCard
          label="Records in view"
          value={formatInteger(data.total_records_after_filter)}
          hint={`of ${formatInteger(data.total_records_before_filter)} loaded`}
        />
      </div>

      <ChartCard
        title="Field completeness"
        description="Percent complete by field."
        isEmpty={fieldKeys.length === 0}
        table={completenessTable}
      >
        <BarChart
          categories={completenessBar.categories}
          values={completenessBar.values}
          horizontal
          valueName="% complete"
          color="#10b981"
          ariaLabel="Field completeness percentage"
        />
      </ChartCard>

      <ChartCard
        title="Missing values by field"
        description="Missing records by field."
        isEmpty={fieldKeys.length === 0}
        table={missingTable}
      >
        <BarChart
          categories={missingBar.categories}
          values={missingBar.values}
          horizontal
          valueName="Missing records"
          color="#ef4444"
          ariaLabel="Missing values by field"
        />
      </ChartCard>
    </div>
  );
}
