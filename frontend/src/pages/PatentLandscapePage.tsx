import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import { getAnalytics } from "../api/analytics";
import {
  getFocusedLandscape,
  getLandscape,
  getLandscapeFilterOptions,
} from "../api/landscape";
import { encodeAnalysisId } from "../api/patents";
import { Badge } from "../components/common/Badge";
import { Callout } from "../components/common/Callout";
import { DatasetWarningCallout } from "../components/common/DatasetWarningCallout";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { PageHeader } from "../components/common/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { LandscapeCommandBar } from "../components/landscape/LandscapeCommandBar";
import {
  GROUP_COLORS,
  LandscapeMiniGraph,
  colorForGroup,
} from "../components/landscape/LandscapeMiniGraph";
import { MapGraphControls } from "../components/landscape/MapGraphControls";
import { MapWhiteSpacePanel } from "../components/landscape/MapWhiteSpacePanel";
import { RelationshipDensityPanel } from "../components/landscape/RelationshipDensityPanel";
import {
  DEFAULT_PRESET,
  MAP_PRESETS,
  matchPreset,
  withGraphParams,
  type GraphParamKey,
  type GraphParams,
  type GraphSelection,
  type PresetKey,
} from "../components/landscape/mapGraphPresets";
import { buildGroupDensityModel } from "../components/landscape/groupDensitySignal";
import { buildOverviewWhiteSpace } from "../components/opportunity/buildOverviewWhiteSpace";
import {
  EMPTY_LANDSCAPE_FILTER_FORM,
  LANDSCAPE_SOURCES,
  buildActiveFilterChips,
  buildLandscapeQueryFromForm,
  countOptions,
  countSuffix,
  formatInteger,
  hasActiveLandscapeFilters,
  isLandscapeFilterFormEmpty,
  mergeOptions,
  yearPlaceholder,
  type LandscapeFilterFormState,
} from "../components/filters/patentFilterModel";
import { buildLandscapeOpportunitySignals } from "../components/opportunity/buildLandscapeOpportunitySignals";
import {
  OpportunitySignalsPanel,
  type OpportunityScope,
} from "../components/opportunity/OpportunitySignalsPanel";
import { useFilters } from "../state/FilterProvider";
import type { AnalyticsResponse } from "../types/analytics";
import type {
  LandscapeActiveFilters,
  LandscapeEdge,
  LandscapeNode,
  LandscapeResponse,
  LandscapeTechnologyGroup,
} from "../types/landscape";
import type { FilterOptionsResponse } from "../types/patents";

const SAFETY_NOTE =
  "Decision-support only. Similarity, overlap, and group signals are not legal advice.";

const PREVIEW_NEIGHBORS = 8;
const TABLE_PAGE_SIZE = 25;

const STRENGTH_RANK: Record<string, number> = {
  strong: 3,
  moderate: 2,
  weak: 1,
};

function formatScore(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function buildNodeIndex(nodes: LandscapeNode[]): Map<string, LandscapeNode> {
  const map = new Map<string, LandscapeNode>();
  for (const node of nodes) map.set(node.analysis_id, node);
  return map;
}

function averageSimilarity(edges: LandscapeEdge[]): number | null {
  if (edges.length === 0) return null;
  let sum = 0;
  for (const edge of edges) sum += edge.similarity_score;
  return sum / edges.length;
}

function strongestEdge(edges: LandscapeEdge[]): LandscapeEdge | null {
  if (edges.length === 0) return null;
  let best = edges[0];
  for (const edge of edges) {
    if (edge.similarity_score > best.similarity_score) best = edge;
  }
  return best;
}

function similarityBounds(edges: LandscapeEdge[]): {
  min: number;
  max: number;
} {
  if (edges.length === 0) return { min: 0, max: 1 };
  let min = edges[0].similarity_score;
  let max = edges[0].similarity_score;
  for (const edge of edges) {
    if (edge.similarity_score < min) min = edge.similarity_score;
    if (edge.similarity_score > max) max = edge.similarity_score;
  }
  if (min === max) {
    return { min: Math.max(0, min - 0.05), max: Math.min(1, max + 0.05) };
  }
  return { min, max };
}

export function PatentLandscapePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialFocus = searchParams.get("focus");
  const [focusInput, setFocusInput] = useState(initialFocus ?? "");
  const [focusedId, setFocusedId] = useState<string | null>(initialFocus);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [threshold, setThreshold] = useState<number | null>(null);
  const [activeGroupIds, setActiveGroupIds] = useState<Set<number> | null>(
    null,
  );
  // Five backend graph parameters are controlled by the
  // Tighter/Balanced/Broader presets and the Advanced expander. They stay out
  // of URL-backed corpus filters because they tune graph presentation rather
  // than record selection. They default to Balanced and reset on remount.
  const [graphParams, setGraphParams] = useState<GraphParams>(
    () => MAP_PRESETS[DEFAULT_PRESET].params,
  );
  const [densityMode, setDensityMode] = useState(false);
  const presetSelection: GraphSelection = matchPreset(graphParams);
  // Patent filters are the app-level spine: the applied set lives in the URL via
  // the shared FilterProvider so it persists across Map/Trends/Overview, is
  // shareable, and survives reload. The Map's graph-tuning controls (threshold,
  // active groups, focus) stay local below.
  const {
    filters: landscapeFilters,
    form: appliedFilterForm,
    setFilters: setSharedFilters,
    resetFilters: resetSharedFilters,
  } = useFilters();
  const [filterForm, setFilterForm] = useState<LandscapeFilterFormState>(
    () => appliedFilterForm,
  );

  // Re-seed the local editing buffer whenever the shared applied filters change
  // (navigating in from another view, a shared link, reload, or back/forward).
  // Typing only mutates the buffer — not the applied filters — so unapplied
  // edits are preserved until Apply.
  const appliedFilterFormKey = JSON.stringify(appliedFilterForm);
  useEffect(() => {
    setFilterForm(appliedFilterForm);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appliedFilterFormKey]);

  // Keep the focus query param in sync with focusedId so deep links stay
  // shareable. We read the latest params through a ref instead of listing
  // `searchParams` in the deps: the shared FilterProvider also owns the URL, so
  // depending on the `searchParams` identity here would make this effect re-run
  // (and re-write `focus`) every time a filter write changes that identity,
  // producing a focus↔filter ping-pong ("Maximum update depth exceeded"). The
  // `current === next` guard ensures we never write unless `focus` truly changed.
  const searchParamsRef = useRef(searchParams);
  searchParamsRef.current = searchParams;
  useEffect(() => {
    const params = searchParamsRef.current;
    const current = params.get("focus");
    const next = focusedId ?? null;
    if (current === next) return;
    const nextParams = new URLSearchParams(params);
    if (next === null) nextParams.delete("focus");
    else nextParams.set("focus", next);
    setSearchParams(nextParams, { replace: true });
  }, [focusedId, setSearchParams]);

  // When the URL changes externally (e.g. a profile link), reflect it in state.
  useEffect(() => {
    const param = searchParams.get("focus");
    setFocusedId((current) => (current === param ? current : param));
    setFocusInput((current) => (current === (param ?? "") ? current : param ?? ""));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.get("focus")]);

  // Combine shared corpus filters with Map-local graph parameters for the
  // backend request. Filter changes refresh every view; graph changes refresh
  // only the Map.
  const effectiveQuery = useMemo(
    () => withGraphParams(landscapeFilters, graphParams),
    [landscapeFilters, graphParams],
  );

  const filterOptionsQuery = useQuery({
    queryKey: ["landscape", "filter-options"],
    queryFn: ({ signal }) => getLandscapeFilterOptions(signal),
  });

  const landscapeQuery = useQuery({
    queryKey: ["landscape", effectiveQuery],
    queryFn: ({ signal }) => getLandscape(effectiveQuery, signal),
    placeholderData: keepPreviousData,
  });

  const focusedQuery = useQuery({
    queryKey: ["landscape", "focused", focusedId, effectiveQuery],
    queryFn: ({ signal }) =>
      getFocusedLandscape(focusedId ?? "", effectiveQuery, signal),
    enabled: focusedId !== null && focusedId.length > 0,
    placeholderData: keepPreviousData,
  });

  // White space reuses the same defensible logic as Overview, which reads the
  // analytics endpoint. Sharing the ["analytics", filters] key with Overview /
  // Trends means a filter applied on any of them warms this cache. The graph
  // params are deliberately excluded — white space is about the corpus slice.
  const analyticsQuery = useQuery({
    queryKey: ["analytics", landscapeFilters],
    queryFn: ({ signal }) => getAnalytics(landscapeFilters, signal),
    placeholderData: keepPreviousData,
  });

  const activeData: LandscapeResponse | undefined =
    focusedId && focusedQuery.data ? focusedQuery.data : landscapeQuery.data;

  const data = activeData ?? landscapeQuery.data;

  // Reset selection/hover and threshold when underlying data changes meaningfully.
  useEffect(() => {
    setSelectedId(null);
    setHoveredId(null);
  }, [focusedId, landscapeFilters]);

  // Initialize threshold to the data's minimum similarity once data loads.
  useEffect(() => {
    if (!data) return;
    if (threshold !== null) return;
    const bounds = similarityBounds(data.edges);
    setThreshold(Number(bounds.min.toFixed(3)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.edges.length]);

  const applyLandscapeFilters = () => {
    setSharedFilters(buildLandscapeQueryFromForm(filterForm));
    setSelectedId(null);
    setHoveredId(null);
    setActiveGroupIds(null);
  };

  const resetLandscapeFilters = () => {
    setFilterForm({ ...EMPTY_LANDSCAPE_FILTER_FORM, sources: [] });
    resetSharedFilters();
    setSelectedId(null);
    setHoveredId(null);
    setActiveGroupIds(null);
  };

  const selectPreset = (preset: PresetKey) => {
    setGraphParams(MAP_PRESETS[preset].params);
  };

  const changeGraphParam = (key: GraphParamKey, value: number) => {
    setGraphParams((prev) => ({ ...prev, [key]: value }));
  };

  // White-space doorway: apply the chosen application area onto the shared spine
  // (keeping any other active filters) so the whole Map re-reads that slice. This
  // carries the spine just like the Overview white-space cards do.
  const applyAreaFacet = (area: string) => {
    setSharedFilters({ ...landscapeFilters, application_area: area });
    setSelectedId(null);
    setHoveredId(null);
    setActiveGroupIds(null);
  };

  if (landscapeQuery.isPending && !landscapeQuery.data) {
    return (
      <section>
        <LandscapeHeader />
        <LoadingState message="Loading map workspace..." />
      </section>
    );
  }

  if ((landscapeQuery.isError || !landscapeQuery.data) && !landscapeQuery.data) {
    const err = landscapeQuery.error;
    return (
      <section>
        <LandscapeHeader />
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

  const loadedCorpusCount =
    landscapeQuery.data.total_records_before_filter ??
    landscapeQuery.data.node_count;

  if (landscapeQuery.data.node_count === 0 && loadedCorpusCount === 0) {
    return (
      <section>
        <LandscapeHeader />
        <EmptyState
          title="No map to explore"
          message="Load a curated source-labeled corpus to populate the map."
          actions={
            <Link className="link-button" to="/data-sources">
              Go to Corpus & Sources →
            </Link>
          }
        />
      </section>
    );
  }

  if (!data) {
    return (
      <section>
        <LandscapeHeader />
        <LoadingState message="Loading map workspace..." />
      </section>
    );
  }

  return (
    <LandscapeContent
      data={data}
      isFocused={focusedId !== null}
      focusedId={focusedId}
      focusInput={focusInput}
      focusedQuery={focusedQuery}
      selectedId={selectedId}
      hoveredId={hoveredId}
      threshold={threshold}
      activeGroupIds={activeGroupIds}
      filterForm={filterForm}
      filterMetadata={filterOptionsQuery.data}
      filterMetadataError={filterOptionsQuery.error}
      filterMetadataIsLoading={filterOptionsQuery.isPending}
      landscapeError={landscapeQuery.isError ? landscapeQuery.error : null}
      isLandscapeFetching={landscapeQuery.isFetching || focusedQuery.isFetching}
      graphParams={graphParams}
      presetSelection={presetSelection}
      densityMode={densityMode}
      analytics={analyticsQuery.data}
      analyticsIsLoading={analyticsQuery.isPending && !analyticsQuery.data}
      appliedArea={landscapeFilters.application_area}
      onSelectPreset={selectPreset}
      onChangeGraphParam={changeGraphParam}
      onToggleDensity={setDensityMode}
      onApplyArea={applyAreaFacet}
      onThresholdChange={setThreshold}
      onActiveGroupIdsChange={setActiveGroupIds}
      onFilterFormChange={setFilterForm}
      onApplyFilters={applyLandscapeFilters}
      onResetFilters={resetLandscapeFilters}
      onHoverNode={setHoveredId}
      onSelectNode={setSelectedId}
      onFocusInputChange={setFocusInput}
      onSubmitFocus={(event) => {
        event.preventDefault();
        const trimmed = focusInput.trim();
        setFocusedId(trimmed.length > 0 ? trimmed : null);
      }}
      onClearFocus={() => {
        setFocusInput("");
        setFocusedId(null);
      }}
      onFocusOnNode={(analysisId) => {
        setFocusInput(analysisId);
        setFocusedId(analysisId);
      }}
      onOpenNode={(analysisId) =>
        navigate(`/patents/${encodeAnalysisId(analysisId)}`)
      }
    />
  );
}

interface LandscapeContentProps {
  data: LandscapeResponse;
  isFocused: boolean;
  focusedId: string | null;
  focusInput: string;
  focusedQuery: {
    isFetching: boolean;
    isError: boolean;
    error: unknown;
  };
  selectedId: string | null;
  hoveredId: string | null;
  threshold: number | null;
  activeGroupIds: Set<number> | null;
  filterForm: LandscapeFilterFormState;
  filterMetadata: FilterOptionsResponse | undefined;
  filterMetadataError: unknown;
  filterMetadataIsLoading: boolean;
  landscapeError: unknown;
  isLandscapeFetching: boolean;
  graphParams: GraphParams;
  presetSelection: GraphSelection;
  densityMode: boolean;
  analytics: AnalyticsResponse | undefined;
  analyticsIsLoading: boolean;
  appliedArea: string | undefined;
  onSelectPreset: (preset: PresetKey) => void;
  onChangeGraphParam: (key: GraphParamKey, value: number) => void;
  onToggleDensity: (value: boolean) => void;
  onApplyArea: (area: string) => void;
  onThresholdChange: (value: number) => void;
  onActiveGroupIdsChange: (value: Set<number> | null) => void;
  onFilterFormChange: (value: LandscapeFilterFormState) => void;
  onApplyFilters: () => void;
  onResetFilters: () => void;
  onHoverNode: (id: string | null) => void;
  onSelectNode: (id: string | null) => void;
  onFocusInputChange: (value: string) => void;
  onSubmitFocus: (event: React.FormEvent) => void;
  onClearFocus: () => void;
  onFocusOnNode: (analysisId: string) => void;
  onOpenNode: (analysisId: string) => void;
}

function LandscapeContent(props: LandscapeContentProps) {
  const {
    data,
    isFocused,
    focusedId,
    focusInput,
    focusedQuery,
    selectedId,
    hoveredId,
    threshold,
    activeGroupIds,
    filterForm,
    filterMetadata,
    filterMetadataError,
    filterMetadataIsLoading,
    landscapeError,
    isLandscapeFetching,
    graphParams,
    presetSelection,
    densityMode,
    analytics,
    analyticsIsLoading,
    appliedArea,
    onSelectPreset,
    onChangeGraphParam,
    onToggleDensity,
    onApplyArea,
    onThresholdChange,
    onActiveGroupIdsChange,
    onFilterFormChange,
    onApplyFilters,
    onResetFilters,
    onHoverNode,
    onSelectNode,
    onFocusInputChange,
    onSubmitFocus,
    onClearFocus,
    onFocusOnNode,
    onOpenNode,
  } = props;

  const nodeIndex = useMemo(() => buildNodeIndex(data.nodes), [data.nodes]);
  const bounds = useMemo(() => similarityBounds(data.edges), [data.edges]);
  const effectiveThreshold = Math.min(
    bounds.max,
    Math.max(bounds.min, threshold ?? bounds.min),
  );

  const visibleNodeIds = useMemo<Set<string>>(() => {
    if (activeGroupIds === null) {
      return new Set(data.nodes.map((n) => n.analysis_id));
    }
    return new Set(
      data.nodes
        .filter(
          (n) =>
            n.technology_group_id === null ||
            activeGroupIds.has(n.technology_group_id),
        )
        .map((n) => n.analysis_id),
    );
  }, [activeGroupIds, data.nodes]);

  const filteredEdges = useMemo(
    () =>
      data.edges.filter(
        (edge) =>
          edge.similarity_score >= effectiveThreshold &&
          visibleNodeIds.has(edge.source_analysis_id) &&
          visibleNodeIds.has(edge.target_analysis_id),
      ),
    [data.edges, effectiveThreshold, visibleNodeIds],
  );

  const visibleNodes = useMemo(
    () => data.nodes.filter((n) => visibleNodeIds.has(n.analysis_id)),
    [data.nodes, visibleNodeIds],
  );

  const visibleDegree = useMemo(() => {
    const map = new Map<string, number>();
    for (const node of visibleNodes) map.set(node.analysis_id, 0);
    for (const edge of filteredEdges) {
      map.set(
        edge.source_analysis_id,
        (map.get(edge.source_analysis_id) ?? 0) + 1,
      );
      map.set(
        edge.target_analysis_id,
        (map.get(edge.target_analysis_id) ?? 0) + 1,
      );
    }
    return map;
  }, [visibleNodes, filteredEdges]);

  const avgSimilarity = averageSimilarity(filteredEdges);
  const strongest = strongestEdge(filteredEdges);

  const selectedNode = selectedId ? nodeIndex.get(selectedId) ?? null : null;
  const focusedNode = focusedId ? nodeIndex.get(focusedId) ?? null : null;
  const selectedNeighbors = useMemo<LandscapeEdge[]>(() => {
    if (!selectedId) return [];
    return filteredEdges
      .filter(
        (e) =>
          e.source_analysis_id === selectedId ||
          e.target_analysis_id === selectedId,
      )
      .sort((a, b) => b.similarity_score - a.similarity_score);
  }, [filteredEdges, selectedId]);

  const activeGroupsCount =
    activeGroupIds === null ? data.technology_group_count : activeGroupIds.size;

  const opportunitySignals = useMemo(
    () =>
      buildLandscapeOpportunitySignals({
        groups: data.technology_groups,
        visibleNodes,
        filteredEdges,
      }),
    [data.technology_groups, visibleNodes, filteredEdges],
  );

  // Density model (Crowded/Sparse tiers + per-group weights for the density-mode
  // halos), derived from patent_count of the in-view technology groups.
  const densityModel = useMemo(
    () => buildGroupDensityModel(data.technology_groups),
    [data.technology_groups],
  );
  const densityGroupWeight = useMemo(() => {
    const map = new Map<number, number>();
    for (const [id, signal] of densityModel.byGroupId) {
      map.set(id, signal.weight);
    }
    return map;
  }, [densityModel]);

  // White space reuses the Overview's logic over the same filter-aware analytics
  // slice, so the Map lists exactly the areas the Overview would for this filter.
  const whiteSpace = useMemo(
    () => (analytics ? buildOverviewWhiteSpace(analytics) : null),
    [analytics],
  );

  const viewControlsActive =
    activeGroupIds !== null || effectiveThreshold > bounds.min;
  const backendFiltersActive = hasActiveLandscapeFilters(data.active_filters);
  const opportunityScope: OpportunityScope = isFocused
    ? "focused-neighborhood"
    : viewControlsActive || backendFiltersActive
    ? "current-visible"
    : "full-corpus";

  return (
    <section>
      <LandscapeHeader />

      <LandscapeCommandBar
        totalPatents={data.node_count}
        visiblePatents={visibleNodes.length}
        totalEdges={data.edges.length}
        visibleEdges={filteredEdges.length}
        totalGroups={data.technology_group_count}
        activeGroupsCount={activeGroupsCount}
        threshold={effectiveThreshold}
        isFocused={isFocused}
        focusedId={focusedId}
        focusedNode={focusedNode}
        selectedNode={selectedNode}
        onClearFocus={onClearFocus}
        onClearSelection={() => onSelectNode(null)}
      />

      <Callout variant="info" title="Decision-support only">
        <p>{SAFETY_NOTE}</p>
      </Callout>

      <DatasetWarningCallout warnings={data.warnings} />

      {landscapeError !== null && landscapeError !== undefined && (
        <ErrorState
          title="Filters could not be applied"
          message={
            landscapeError instanceof ApiError
              ? landscapeError.detail
              : String(landscapeError)
          }
          hint="Check the filter values and apply again. The previous map remains visible while you adjust them."
        />
      )}

      <LandscapeFilterPanel
        form={filterForm}
        metadata={filterMetadata}
        metadataError={filterMetadataError}
        metadataIsLoading={filterMetadataIsLoading}
        activeFilters={data.active_filters}
        filteredCount={data.total_records_after_filter ?? data.node_count}
        totalCount={data.total_records_before_filter ?? data.node_count}
        isFetching={isLandscapeFetching}
        onChange={onFilterFormChange}
        onApply={onApplyFilters}
        onReset={onResetFilters}
      />

      <SectionCard
        title={
          isFocused
            ? "Focused relationship neighborhood"
            : "Map workspace"
        }
        description={
          isFocused
            ? "Focused patent and its strongest related patents."
            : "Text-similarity groups, relationship strength, and overlap signals."
        }
        actions={
          isFocused && (
            <button
              type="button"
              className="button button--ghost button--sm"
              onClick={onClearFocus}
            >
              Exit focused view
            </button>
          )
        }
      >
        {focusedId && focusedQuery.isFetching && (
          <LoadingState message={`Focusing map on ${focusedId}...`} />
        )}

        {focusedId && focusedQuery.isError && (
          <ErrorState
            title="Focused view failed"
            message={
              focusedQuery.error instanceof ApiError
                ? focusedQuery.error.detail
                : focusedQuery.error
                ? String(focusedQuery.error)
                : "Unknown error"
            }
            hint="Use a valid analysis_id (e.g. one of the IDs from the relationship table)."
          />
        )}

        <div className="landscape-workspace">
          <aside
            className="landscape-workspace__controls"
            aria-label="Map reading controls"
          >
            <MapGraphControls
              selection={presetSelection}
              params={graphParams}
              onSelectPreset={onSelectPreset}
              onChangeParam={onChangeGraphParam}
              densityMode={densityMode}
              onToggleDensity={onToggleDensity}
              isFetching={isLandscapeFetching}
            />
            <LandscapeControls
              bounds={bounds}
              threshold={effectiveThreshold}
              onThresholdChange={onThresholdChange}
              groups={data.technology_groups}
              activeGroupIds={activeGroupIds}
              onActiveGroupIdsChange={onActiveGroupIdsChange}
              visibleNodeCount={visibleNodes.length}
              visibleEdgeCount={filteredEdges.length}
              totalEdgeCount={data.edges.length}
            />
          </aside>

          <div className="landscape-workspace__canvas">
            <NeighborhoodSummaryStrip
              isFocused={isFocused}
              focusedNode={focusedNode}
              selectedNode={selectedNode}
              visibleNodes={visibleNodes.length}
              visibleEdges={filteredEdges.length}
              selectedNeighborsCount={selectedNeighbors.length}
              strongestVisible={strongest}
              avgSimilarity={avgSimilarity}
            />
            {data.node_count === 0 && backendFiltersActive ? (
              <EmptyState
                title="No patents match these filters"
                message="Widen the filters or reset to the full corpus."
                actions={
                  <button
                    type="button"
                    className="button button--ghost button--sm"
                    onClick={onResetFilters}
                  >
                    Reset filters
                  </button>
                }
              />
            ) : (
              <>
                <LandscapeMiniGraph
                  data={data}
                  edges={filteredEdges}
                  visibleNodeIds={visibleNodeIds}
                  selectedId={selectedId}
                  hoveredId={hoveredId}
                  onHoverNode={onHoverNode}
                  onSelectNode={onSelectNode}
                  onOpenNode={onOpenNode}
                  densityMode={densityMode}
                  groupWeight={densityGroupWeight}
                />
                <LandscapeLegend groups={data.technology_groups} />
              </>
            )}
          </div>

          <aside
            className="landscape-workspace__inspector"
            aria-label="Selected patent inspector"
          >
            {selectedNode ? (
              <SelectedPatentPanel
                node={selectedNode}
                neighbors={selectedNeighbors}
                nodeIndex={nodeIndex}
                visibleDegree={visibleDegree.get(selectedNode.analysis_id) ?? 0}
                onOpen={() => onOpenNode(selectedNode.analysis_id)}
                onFocusHere={() => onFocusOnNode(selectedNode.analysis_id)}
                onClear={() => onSelectNode(null)}
                onSelectNeighbor={(id) => onSelectNode(id)}
                isFocusedView={isFocused}
              />
            ) : (
              <EmptyPreview />
            )}
          </aside>
        </div>
      </SectionCard>

      {whiteSpace ? (
        <MapWhiteSpacePanel
          whiteSpace={whiteSpace}
          groups={data.technology_groups}
          density={densityModel}
          densityMode={densityMode}
          appliedArea={appliedArea}
          onApplyArea={onApplyArea}
        />
      ) : (
        analyticsIsLoading && (
          <SectionCard title="White space & density">
            <LoadingState message="Reading white-space signals..." />
          </SectionCard>
        )
      )}

      <RelationshipDensityPanel
        groups={data.technology_groups}
        visibleNodes={visibleNodes}
        filteredEdges={filteredEdges}
        isFocused={isFocused}
      />

      <OpportunitySignalsPanel
        signals={opportunitySignals}
        scope={opportunityScope}
        emptyMessage="No signals for this view. Loosen the threshold or include more groups."
      />

      <FocusedControl
        focusInput={focusInput}
        focusedId={focusedId}
        onChange={onFocusInputChange}
        onSubmit={onSubmitFocus}
        onClear={onClearFocus}
      />

      <TechnologyGroupsSection groups={data.technology_groups} />

      <RelationshipsTable
        edges={filteredEdges}
        totalEdges={data.edges.length}
        nodeIndex={nodeIndex}
        threshold={effectiveThreshold}
        selectedId={selectedId}
        onSelect={onSelectNode}
      />
    </section>
  );
}

interface LandscapeFilterPanelProps {
  form: LandscapeFilterFormState;
  metadata: FilterOptionsResponse | undefined;
  metadataError: unknown;
  metadataIsLoading: boolean;
  activeFilters: LandscapeActiveFilters;
  filteredCount: number;
  totalCount: number;
  isFetching: boolean;
  onChange: (value: LandscapeFilterFormState) => void;
  onApply: () => void;
  onReset: () => void;
}

function LandscapeFilterPanel({
  form,
  metadata,
  metadataError,
  metadataIsLoading,
  activeFilters,
  filteredCount,
  totalCount,
  isFetching,
  onChange,
  onApply,
  onReset,
}: LandscapeFilterPanelProps) {
  const publicationRange = metadata?.publication_year_range;
  const filingRange = metadata?.filing_year_range;
  const countryOptions = mergeOptions(metadata?.countries);
  const assigneeOptions = mergeOptions(
    countOptions(metadata?.top_assignees),
    metadata?.assignees,
  );
  const keywordOptions = mergeOptions(countOptions(metadata?.top_keywords));
  const applicationAreaOptions = mergeOptions(
    countOptions(metadata?.top_application_areas),
    metadata?.candidate_application_areas,
  );
  const classificationOptions = mergeOptions(
    countOptions(metadata?.top_classifications),
    metadata?.classifications,
  );
  const activeFilterChips = buildActiveFilterChips(activeFilters);
  const resetDisabled =
    isLandscapeFilterFormEmpty(form) &&
    !hasActiveLandscapeFilters(activeFilters);

  const updateField = <Key extends keyof LandscapeFilterFormState>(
    key: Key,
    value: LandscapeFilterFormState[Key],
  ) => {
    onChange({ ...form, [key]: value });
  };

  const toggleSource = (source: string, checked: boolean) => {
    const next = checked
      ? [...form.sources, source]
      : form.sources.filter((item) => item !== source);
    updateField(
      "sources",
      LANDSCAPE_SOURCES.filter((item) => next.includes(item)),
    );
  };

  return (
    <SectionCard
      title="Patent map filters"
      description="Corpus slice for the map. Display controls stay local."
    >
      <form
        className="landscape-filter-panel"
        onSubmit={(event) => {
          event.preventDefault();
          onApply();
        }}
      >
        <div className="landscape-filter-panel__summary" aria-live="polite">
          <span>
            Showing <strong>{formatInteger(filteredCount)}</strong> of{" "}
            <strong>{formatInteger(totalCount)}</strong> patents.
          </span>
          {isFetching && (
            <span className="landscape-filter-panel__updating">
              <span className="loading-state__spinner" aria-hidden="true" />
              Updating map...
            </span>
          )}
        </div>

        {metadataIsLoading && (
          <p className="filter-bar__hint">Loading filter metadata...</p>
        )}

        {metadataError !== null && metadataError !== undefined && (
          <Callout variant="warning" title="Filter options unavailable">
            <p>
              {metadataError instanceof ApiError
                ? metadataError.detail
                : String(metadataError)}
            </p>
          </Callout>
        )}

        <fieldset className="landscape-filter-panel__fieldset">
          <legend className="filter-field__label">Source authority</legend>
          <div className="landscape-filter-panel__sources">
            {LANDSCAPE_SOURCES.map((source) => (
              <label key={source} className="source-checkbox">
                <input
                  type="checkbox"
                  checked={form.sources.includes(source)}
                  onChange={(event) =>
                    toggleSource(source, event.target.checked)
                  }
                />
                <span>{source}</span>
                <span className="source-checkbox__count">
                  {countSuffix(metadata?.source_counts[source])}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="filter-bar__row">
          <label className="filter-field">
            <span className="filter-field__label">Publication from</span>
            <input
              type="number"
              value={form.publicationYearFrom}
              min={publicationRange?.min ?? undefined}
              max={publicationRange?.max ?? undefined}
              placeholder={yearPlaceholder(publicationRange?.min)}
              onChange={(event) =>
                updateField("publicationYearFrom", event.target.value)
              }
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Publication to</span>
            <input
              type="number"
              value={form.publicationYearTo}
              min={publicationRange?.min ?? undefined}
              max={publicationRange?.max ?? undefined}
              placeholder={yearPlaceholder(publicationRange?.max)}
              onChange={(event) =>
                updateField("publicationYearTo", event.target.value)
              }
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Filing from</span>
            <input
              type="number"
              value={form.filingYearFrom}
              min={filingRange?.min ?? undefined}
              max={filingRange?.max ?? undefined}
              placeholder={yearPlaceholder(filingRange?.min)}
              onChange={(event) =>
                updateField("filingYearFrom", event.target.value)
              }
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Filing to</span>
            <input
              type="number"
              value={form.filingYearTo}
              min={filingRange?.min ?? undefined}
              max={filingRange?.max ?? undefined}
              placeholder={yearPlaceholder(filingRange?.max)}
              onChange={(event) =>
                updateField("filingYearTo", event.target.value)
              }
            />
          </label>
        </div>

        <div className="filter-bar__row">
          <label className="filter-field">
            <span className="filter-field__label">Country</span>
            <input
              type="search"
              list="landscape-country-options"
              value={form.country}
              placeholder="All countries"
              autoComplete="off"
              onChange={(event) => updateField("country", event.target.value)}
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Application area</span>
            <input
              type="search"
              list="landscape-application-area-options"
              value={form.applicationArea}
              placeholder="All application areas"
              autoComplete="off"
              onChange={(event) =>
                updateField("applicationArea", event.target.value)
              }
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Assignee</span>
            <input
              type="text"
              list="landscape-assignee-options"
              value={form.assignee}
              placeholder="Assignee contains..."
              autoComplete="off"
              onChange={(event) => updateField("assignee", event.target.value)}
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Keyword</span>
            <input
              type="text"
              list="landscape-keyword-options"
              value={form.keyword}
              placeholder="Title, abstract, keyword..."
              autoComplete="off"
              onChange={(event) => updateField("keyword", event.target.value)}
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Classification</span>
            <input
              type="text"
              list="landscape-classification-options"
              value={form.classification}
              placeholder="IPC or CPC prefix..."
              autoComplete="off"
              onChange={(event) =>
                updateField("classification", event.target.value)
              }
            />
          </label>
        </div>

        <datalist id="landscape-country-options">
          {countryOptions.map((country) => (
            <option
              key={country}
              value={country}
              label={`${country}${countSuffix(metadata?.country_counts[country])}`}
            />
          ))}
        </datalist>
        <datalist id="landscape-assignee-options">
          {assigneeOptions.map((assignee) => (
            <option
              key={assignee}
              value={assignee}
              label={`${assignee}${countSuffix(metadata?.top_assignees[assignee])}`}
            />
          ))}
        </datalist>
        <datalist id="landscape-keyword-options">
          {keywordOptions.map((keyword) => (
            <option
              key={keyword}
              value={keyword}
              label={`${keyword}${countSuffix(metadata?.top_keywords[keyword])}`}
            />
          ))}
        </datalist>
        <datalist id="landscape-application-area-options">
          {applicationAreaOptions.map((area) => (
            <option
              key={area}
              value={area}
              label={`${area}${countSuffix(
                metadata?.top_application_areas[area],
              )}`}
            />
          ))}
        </datalist>
        <datalist id="landscape-classification-options">
          {classificationOptions.map((classification) => (
            <option
              key={classification}
              value={classification}
              label={`${classification}${countSuffix(
                metadata?.top_classifications[classification],
              )}`}
            />
          ))}
        </datalist>

        <div className="filter-bar__actions">
          <div className="landscape-filter-panel__chips" aria-live="polite">
            {activeFilterChips.length > 0 ? (
              activeFilterChips.map((chip) => (
                <span key={chip.key} className="chip chip--keyword">
                  {chip.label}
                </span>
              ))
            ) : (
              <span className="chip chip--muted">No corpus filters active</span>
            )}
          </div>
          <div className="landscape-filter-panel__actions">
            <button type="submit" className="button">
              Apply filters
            </button>
            <button
              type="button"
              className="button button--ghost"
              onClick={onReset}
              disabled={resetDisabled}
            >
              Reset filters
            </button>
          </div>
        </div>
      </form>
    </SectionCard>
  );
}

interface NeighborhoodSummaryStripProps {
  isFocused: boolean;
  focusedNode: LandscapeNode | null;
  selectedNode: LandscapeNode | null;
  visibleNodes: number;
  visibleEdges: number;
  selectedNeighborsCount: number;
  strongestVisible: LandscapeEdge | null;
  avgSimilarity: number | null;
}

function NeighborhoodSummaryStrip({
  isFocused,
  focusedNode,
  selectedNode,
  visibleNodes,
  visibleEdges,
  selectedNeighborsCount,
  strongestVisible,
  avgSimilarity,
}: NeighborhoodSummaryStripProps) {
  const headlineNode = selectedNode ?? focusedNode;
  const eyebrow = selectedNode
    ? "Selected neighborhood"
    : isFocused
    ? "Focused neighborhood"
    : "Workspace summary";
  const headline = headlineNode
    ? headlineNode.title || headlineNode.patent_id
    : `${visibleNodes} patent${visibleNodes === 1 ? "" : "s"} · ${visibleEdges} visible relationship${
        visibleEdges === 1 ? "" : "s"
      }`;

  return (
    <div className="landscape-summary-strip" role="status">
      <div className="landscape-summary-strip__main">
        <span className="landscape-summary-strip__eyebrow">{eyebrow}</span>
        <span className="landscape-summary-strip__title">{headline}</span>
      </div>
      <div className="landscape-summary-strip__stats">
        {selectedNode ? (
          <>
            <span className="landscape-summary-strip__pill">
              <strong>{selectedNeighborsCount}</strong> visible neighbor
              {selectedNeighborsCount === 1 ? "" : "s"}
            </span>
            {selectedNode.technology_group && (
              <span className="landscape-summary-strip__pill">
                {selectedNode.technology_group}
              </span>
            )}
          </>
        ) : (
          <>
            <span className="landscape-summary-strip__pill">
              Avg similarity{" "}
              <strong>{formatScore(avgSimilarity, 2)}</strong>
            </span>
            {strongestVisible && (
              <span className="landscape-summary-strip__pill">
                Strongest visible{" "}
                <strong>
                  {strongestVisible.relationship_strength} (
                  {formatScore(strongestVisible.similarity_score, 2)})
                </strong>
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function LandscapeHeader() {
  return (
    <PageHeader
      eyebrow="Explore"
      title="Map workspace"
      description="Technology groups, relationship neighborhoods, overlap signals, and density for the loaded corpus."
      meta={
        <>
          <Badge variant="primary" withDot>
            Optimized grouping support
          </Badge>
          <Badge variant="neutral">Relationship strength is a reading aid</Badge>
          <Badge variant="accent">Density reading aid</Badge>
        </>
      }
    />
  );
}

interface LandscapeControlsProps {
  bounds: { min: number; max: number };
  threshold: number;
  onThresholdChange: (value: number) => void;
  groups: LandscapeTechnologyGroup[];
  activeGroupIds: Set<number> | null;
  onActiveGroupIdsChange: (value: Set<number> | null) => void;
  visibleNodeCount: number;
  visibleEdgeCount: number;
  totalEdgeCount: number;
}

function LandscapeControls({
  bounds,
  threshold,
  onThresholdChange,
  groups,
  activeGroupIds,
  onActiveGroupIdsChange,
  visibleNodeCount,
  visibleEdgeCount,
  totalEdgeCount,
}: LandscapeControlsProps) {
  const min = Number(bounds.min.toFixed(3));
  const max = Number(bounds.max.toFixed(3));
  const step = 0.005;

  const allGroupIds = useMemo(
    () => groups.map((g) => g.technology_group_id),
    [groups],
  );

  const allSelected = activeGroupIds === null;

  const toggleGroup = (id: number) => {
    const current =
      activeGroupIds === null ? new Set(allGroupIds) : new Set(activeGroupIds);
    if (current.has(id)) {
      current.delete(id);
    } else {
      current.add(id);
    }
    if (current.size === allGroupIds.length) {
      onActiveGroupIdsChange(null);
    } else {
      onActiveGroupIdsChange(current);
    }
  };

  const showAll = () => onActiveGroupIdsChange(null);
  const showNone = () => onActiveGroupIdsChange(new Set());

  return (
    <div className="landscape-controls" role="group" aria-label="Reading controls">
      <header className="landscape-controls__intro">
        <span className="landscape-controls__intro-eyebrow">
          Reading controls
        </span>
        <p className="landscape-controls__intro-body">
          Display filters for the loaded map.
        </p>
      </header>

      <div className="landscape-controls__row">
        <div className="landscape-controls__field">
          <label
            className="landscape-controls__label"
            htmlFor="landscape-threshold"
          >
            Minimum relationship strength
          </label>
          <div className="landscape-controls__slider">
            <input
              id="landscape-threshold"
              type="range"
              min={min}
              max={max}
              step={step}
              value={Math.min(max, Math.max(min, threshold))}
              onChange={(event) =>
                onThresholdChange(Number(event.target.value))
              }
              aria-valuemin={min}
              aria-valuemax={max}
              aria-valuenow={threshold}
              aria-label="Minimum similarity score"
            />
            <span className="landscape-controls__value">
              ≥ {threshold.toFixed(3)}
            </span>
          </div>
          <p className="landscape-controls__hint">
            Showing <strong>{visibleEdgeCount}</strong> relationship
            {visibleEdgeCount === 1 ? "" : "s"}
            {totalEdgeCount > 0 && (
              <>
                {" "}of <strong>{totalEdgeCount}</strong> total
              </>
            )}
            . Strength is cosine text similarity (0–1).
          </p>
        </div>
      </div>

      {groups.length > 0 && (
        <div className="landscape-controls__row">
          <div className="landscape-controls__field">
            <div className="landscape-controls__header">
              <span className="landscape-controls__label">
                Technology groups
              </span>
              <div className="landscape-controls__actions">
                <button
                  type="button"
                  className="button button--subtle button--sm"
                  onClick={showAll}
                  aria-pressed={allSelected}
                >
                  Show all
                </button>
                <button
                  type="button"
                  className="button button--subtle button--sm"
                  onClick={showNone}
                  aria-pressed={
                    activeGroupIds !== null && activeGroupIds.size === 0
                  }
                >
                  Hide all
                </button>
              </div>
            </div>
            <p className="landscape-controls__group-note">
              Text-similarity groups, not legal categories.
            </p>
            <div className="landscape-controls__chips" role="group">
              {groups.map((group) => {
                const active =
                  allSelected ||
                  activeGroupIds!.has(group.technology_group_id);
                return (
                  <button
                    type="button"
                    key={group.technology_group_id}
                    className={`group-toggle${
                      active ? " group-toggle--active" : ""
                    }`}
                    aria-pressed={active}
                    onClick={() => toggleGroup(group.technology_group_id)}
                    title={
                      group.group_label && group.group_label !== group.technology_group
                        ? `${group.technology_group} — ${group.group_label}`
                        : group.technology_group
                    }
                  >
                    <span
                      className="group-toggle__swatch"
                      style={{
                        background: colorForGroup(group.technology_group_id),
                      }}
                      aria-hidden="true"
                    />
                    <span className="group-toggle__label">
                      {group.group_label || group.technology_group}
                    </span>
                    <span className="group-toggle__count">
                      {group.patent_count}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="landscape-controls__hint">
              {allSelected
                ? `All ${groups.length} groups visible · ${visibleNodeCount} patents.`
                : `${
                    activeGroupIds!.size
                  } of ${groups.length} groups · ${visibleNodeCount} patents in view.`}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function LandscapeLegend({ groups }: { groups: LandscapeTechnologyGroup[] }) {
  if (groups.length === 0) return null;
  const top = groups.slice(0, GROUP_COLORS.length);
  return (
    <div className="landscape-legend" aria-label="Technology group colors">
      {top.map((group) => (
        <span key={group.technology_group_id} className="landscape-legend__item">
          <span
            className="landscape-legend__swatch"
            style={{ background: colorForGroup(group.technology_group_id) }}
          />
          {group.group_label || group.technology_group}
        </span>
      ))}
      <span className="landscape-legend__item">
        <span className="landscape-legend__edge" />
        Similarity link (thicker = stronger)
      </span>
    </div>
  );
}

function EmptyPreview() {
  return (
    <div className="landscape-preview landscape-preview--empty">
      <h3 className="landscape-preview__title">Select a patent</h3>
      <p className="landscape-preview__body">
        Preview related patents, source context, and technology-group fit.
      </p>
    </div>
  );
}

interface SelectedPatentPanelProps {
  node: LandscapeNode;
  neighbors: LandscapeEdge[];
  nodeIndex: Map<string, LandscapeNode>;
  visibleDegree: number;
  onOpen: () => void;
  onFocusHere: () => void;
  onClear: () => void;
  onSelectNeighbor: (id: string) => void;
  isFocusedView: boolean;
}

function SelectedPatentPanel({
  node,
  neighbors,
  nodeIndex,
  visibleDegree,
  onOpen,
  onFocusHere,
  onClear,
  onSelectNeighbor,
  isFocusedView,
}: SelectedPatentPanelProps) {
  const trimmed = neighbors.slice(0, PREVIEW_NEIGHBORS);
  return (
    <div className="landscape-preview">
      <header className="landscape-preview__header">
        <span
          className="landscape-preview__swatch"
          style={{ background: colorForGroup(node.technology_group_id) }}
          aria-hidden="true"
        />
        <div className="landscape-preview__heading">
          <h3 className="landscape-preview__title">
            {node.title || node.patent_id}
          </h3>
          <span className="landscape-preview__sub">
            {node.patent_id}
            {node.technology_group ? ` · ${node.technology_group}` : ""}
          </span>
        </div>
        <button
          type="button"
          className="landscape-preview__close"
          onClick={onClear}
          aria-label="Clear selection"
        >
          ×
        </button>
      </header>

      <dl className="landscape-preview__facts">
        <div>
          <dt>Source authority</dt>
          <dd>{node.source_authority || node.source || "—"}</dd>
        </div>
        {node.assignee && (
          <div>
            <dt>Assignee</dt>
            <dd>{node.assignee}</dd>
          </div>
        )}
        {node.country && (
          <div>
            <dt>Country</dt>
            <dd>{node.country}</dd>
          </div>
        )}
        <div>
          <dt>Visible relationships</dt>
          <dd>
            {visibleDegree}
            <span className="landscape-preview__muted">
              {" "}
              / {node.degree} total
            </span>
          </dd>
        </div>
      </dl>

      {node.candidate_application_areas.length > 0 && (
        <div className="landscape-preview__row">
          <span className="landscape-preview__row-label">
            Candidate application areas
          </span>
          <div className="chip-row">
            {node.candidate_application_areas.slice(0, 6).map((area) => (
              <span key={area} className="chip chip--area">
                {area}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="landscape-preview__row">
        <span className="landscape-preview__row-label">
          Strongest related patents
        </span>
        {trimmed.length === 0 ? (
          <p className="landscape-preview__muted">
            No related patents above the current threshold. Lower the
            relationship strength slider to see weaker connections.
          </p>
        ) : (
          <ul className="landscape-preview__neighbors">
            {trimmed.map((edge, idx) => {
              const otherId =
                edge.source_analysis_id === node.analysis_id
                  ? edge.target_analysis_id
                  : edge.source_analysis_id;
              const other = nodeIndex.get(otherId);
              return (
                <li
                  key={`${otherId}-${idx}`}
                  className="landscape-preview__neighbor"
                >
                  <button
                    type="button"
                    className="landscape-preview__neighbor-button"
                    onClick={() => onSelectNeighbor(otherId)}
                  >
                    <span
                      className="landscape-preview__swatch landscape-preview__swatch--inline"
                      style={{
                        background: colorForGroup(
                          other?.technology_group_id ?? null,
                        ),
                      }}
                      aria-hidden="true"
                    />
                    <span className="landscape-preview__neighbor-title">
                      {other?.title || other?.patent_id || otherId}
                    </span>
                  </button>
                  <span className="landscape-preview__neighbor-meta">
                    <Badge
                      variant={
                        STRENGTH_RANK[edge.relationship_strength.toLowerCase()]
                          ? edge.relationship_strength.toLowerCase() ===
                            "strong"
                            ? "success"
                            : edge.relationship_strength.toLowerCase() ===
                              "moderate"
                            ? "primary"
                            : "neutral"
                          : "neutral"
                      }
                    >
                      {edge.relationship_strength}
                    </Badge>
                    <span className="landscape-preview__neighbor-score">
                      {edge.similarity_score.toFixed(3)}
                    </span>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="landscape-preview__actions">
        <button type="button" className="button" onClick={onOpen}>
          Open Patent Dossier →
        </button>
        {!isFocusedView && (
          <button
            type="button"
            className="button button--ghost"
            onClick={onFocusHere}
          >
            Focus map here
          </button>
        )}
      </div>
    </div>
  );
}

interface FocusedControlProps {
  focusInput: string;
  focusedId: string | null;
  onChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
  onClear: () => void;
}

function FocusedControl({
  focusInput,
  focusedId,
  onChange,
  onSubmit,
  onClear,
}: FocusedControlProps) {
  return (
    <SectionCard
      title="Focused relationship neighborhood"
      description={
        <>
          Focus the map on an <code>analysis_id</code>.
        </>
      }
    >
      <form className="focused-form" onSubmit={onSubmit}>
        <input
          type="text"
          className="focused-form__input"
          value={focusInput}
          placeholder="analysis_id"
          autoComplete="off"
          onChange={(event) => onChange(event.target.value)}
          aria-label="analysis_id"
        />
        <button
          type="submit"
          className="button"
          disabled={focusInput.trim() === ""}
        >
          Focus
        </button>
        <button
          type="button"
          className="button button--ghost"
          onClick={onClear}
          disabled={focusedId === null && focusInput === ""}
        >
          Clear focus
        </button>
      </form>
      {focusedId && (
        <p className="card__muted" style={{ marginTop: "0.6rem" }}>
          Focused neighborhood for <code>{focusedId}</code>.{" "}
          <Link
            className="link-button"
            to={`/patents/${encodeAnalysisId(focusedId)}`}
          >
            Open Patent Dossier →
          </Link>
        </p>
      )}
    </SectionCard>
  );
}

function TechnologyGroupsSection({
  groups,
}: {
  groups: LandscapeTechnologyGroup[];
}) {
  if (groups.length === 0) {
    return (
      <SectionCard title="Technology groups">
        <p className="card__muted">
          No technology groups were computed for this map.
        </p>
      </SectionCard>
    );
  }
  return (
    <SectionCard
      title="Technology groups"
      description="Text-similarity groups for corpus exploration. Grouping quality is the silhouette score (−1 to 1); values near 0 mean groups overlap in wording, which is expected in a narrow single-domain corpus."
    >
      <ul className="tech-group-list">
        {groups.map((group) => (
          <li
            key={group.technology_group_id}
            className="tech-group-list__item"
          >
            <div className="tech-group-list__header">
              <span className="tech-group-list__name">
                <span
                  className="landscape-legend__swatch"
                  style={{
                    background: colorForGroup(group.technology_group_id),
                    marginRight: "0.4rem",
                    verticalAlign: "middle",
                  }}
                />
                {group.technology_group}
                {group.group_label &&
                group.group_label !== group.technology_group
                  ? ` — ${group.group_label}`
                  : ""}
              </span>
              <span className="tech-group-list__count">
                {group.patent_count} patent
                {group.patent_count === 1 ? "" : "s"}
              </span>
            </div>
            {group.grouping_quality && (
              <div className="tech-group-list__meta">
                Grouping quality:{" "}
                <Badge variant="neutral">{group.grouping_quality}</Badge>
                {group.grouping_quality_score !== null
                  ? ` (${formatScore(group.grouping_quality_score)})`
                  : ""}
              </div>
            )}
            {group.top_terms.length > 0 && (
              <div className="tech-group-list__row">
                <span className="patent-card__row-label">Top terms</span>
                <div className="chip-row">
                  {group.top_terms.slice(0, 8).map((term) => (
                    <span key={term} className="chip chip--keyword">
                      {term}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {group.candidate_application_areas.length > 0 && (
              <div className="tech-group-list__row">
                <span className="patent-card__row-label">
                  Candidate application areas
                </span>
                <div className="chip-row">
                  {group.candidate_application_areas
                    .slice(0, 6)
                    .map((area) => (
                      <span key={area.area_name} className="chip chip--area">
                        {area.area_name} · {area.evidence_level}
                      </span>
                    ))}
                </div>
              </div>
            )}
            {group.representative_titles.length > 0 && (
              <details className="tech-group-list__details">
                <summary>Representative titles</summary>
                <ul style={{ margin: "0.4rem 0 0 1rem" }}>
                  {group.representative_titles.slice(0, 5).map((title) => (
                    <li key={title}>{title}</li>
                  ))}
                </ul>
              </details>
            )}
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}

interface RelationshipsTableProps {
  edges: LandscapeEdge[];
  totalEdges: number;
  nodeIndex: Map<string, LandscapeNode>;
  threshold: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function RelationshipsTable({
  edges,
  totalEdges,
  nodeIndex,
  threshold,
  selectedId,
  onSelect,
}: RelationshipsTableProps) {
  const sorted = useMemo(() => {
    const list = [...edges].sort((a, b) => {
      // Prioritize edges incident to the selected node, then by similarity.
      if (selectedId) {
        const aHits =
          a.source_analysis_id === selectedId ||
          a.target_analysis_id === selectedId;
        const bHits =
          b.source_analysis_id === selectedId ||
          b.target_analysis_id === selectedId;
        if (aHits && !bHits) return -1;
        if (!aHits && bHits) return 1;
      }
      return b.similarity_score - a.similarity_score;
    });
    return list.slice(0, TABLE_PAGE_SIZE);
  }, [edges, selectedId]);

  if (totalEdges === 0) {
    return (
      <SectionCard title="Relationship signals">
        <p className="card__muted">
          No relationship signals were produced for this map.
        </p>
      </SectionCard>
    );
  }

  if (sorted.length === 0) {
    return (
      <SectionCard
        title="Relationship signals"
        description={`No relationships visible at similarity ≥ ${threshold.toFixed(
          3,
        )}. Lower the threshold to include weaker links.`}
      >
        <p className="card__muted">
          {totalEdges} total relationships are below the current threshold.
        </p>
      </SectionCard>
    );
  }

  return (
    <SectionCard
      title="Visible relationship signals"
      description={`Top ${sorted.length} of ${edges.length} visible relationship${
        edges.length === 1 ? "" : "s"
      } at similarity ≥ ${threshold.toFixed(
        3,
      )} (cosine text similarity, 0–1). Selected-patent rows are promoted.`}
    >
      <div className="relationships-table__scroll">
        <table className="relationships-table">
          <thead>
            <tr>
              <th scope="col">Source patent</th>
              <th scope="col">Target patent</th>
              <th scope="col">Relationship strength</th>
              <th scope="col">Similarity</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((edge, idx) => {
              const isHit =
                selectedId !== null &&
                (edge.source_analysis_id === selectedId ||
                  edge.target_analysis_id === selectedId);
              return (
                <tr
                  key={`${edge.source_analysis_id}->${edge.target_analysis_id}-${idx}`}
                  className={isHit ? "relationships-table__row--hit" : ""}
                >
                  <td>
                    <RelationshipCell
                      analysisId={edge.source_analysis_id}
                      node={nodeIndex.get(edge.source_analysis_id)}
                      onSelect={onSelect}
                      isSelected={edge.source_analysis_id === selectedId}
                    />
                  </td>
                  <td>
                    <RelationshipCell
                      analysisId={edge.target_analysis_id}
                      node={nodeIndex.get(edge.target_analysis_id)}
                      onSelect={onSelect}
                      isSelected={edge.target_analysis_id === selectedId}
                    />
                  </td>
                  <td>
                    <Badge variant="primary">{edge.relationship_strength}</Badge>
                  </td>
                  <td style={{ fontVariantNumeric: "tabular-nums" }}>
                    {formatScore(edge.similarity_score)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}

function RelationshipCell({
  analysisId,
  node,
  onSelect,
  isSelected,
}: {
  analysisId: string;
  node: LandscapeNode | undefined;
  onSelect: (id: string) => void;
  isSelected: boolean;
}) {
  const label = node?.title || node?.patent_id || analysisId;
  return (
    <div className="relationships-table__cell">
      <button
        type="button"
        className={`relationships-table__title relationships-table__title--button${
          isSelected ? " relationships-table__title--selected" : ""
        }`}
        onClick={() => onSelect(analysisId)}
        title="Select in map"
      >
        {label}
      </button>
      <span className="relationships-table__meta">
        {node && (
          <>
            {[node.patent_id, node.technology_group, node.assignee]
              .filter((part): part is string => Boolean(part))
              .join(" · ")}{" "}
          </>
        )}
        <Link
          className="link-button relationships-table__open"
          to={`/patents/${encodeAnalysisId(analysisId)}`}
        >
          Open dossier →
        </Link>
      </span>
    </div>
  );
}
