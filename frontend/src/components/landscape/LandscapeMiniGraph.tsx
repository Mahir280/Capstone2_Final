import { useMemo, useRef, type ReactNode } from "react";

import type {
  LandscapeEdge,
  LandscapeNode,
  LandscapeResponse,
} from "../../types/landscape";

interface LandscapeMiniGraphProps {
  data: LandscapeResponse;
  height?: number;
  className?: string;
  ariaLabel?: string;
  caption?: ReactNode;
  /** Frontend-filtered edges (after threshold + group filters). */
  edges?: LandscapeEdge[];
  /** Frontend-visible node ids (after group filter). If omitted, all nodes are visible. */
  visibleNodeIds?: Set<string>;
  /** analysis_id of the currently selected node. */
  selectedId?: string | null;
  /** analysis_id of the currently hovered node. */
  hoveredId?: string | null;
  onHoverNode?: (analysisId: string | null) => void;
  onSelectNode?: (analysisId: string | null) => void;
  /** Optional: triggered when user explicitly asks to open the profile (double-click). */
  onOpenNode?: (analysisId: string) => void;
  /**
   * When false, the graph renders as a pure visual (no per-node focus stops,
   * roles, or pointer/keyboard handlers). Used for the Overview density
   * thumbnail so the home page does not expose hundreds of tab stops. Defaults
   * to true to preserve the interactive Map behaviour.
   */
  interactive?: boolean;
  /**
   * When density mode is enabled, nodes in crowded technology groups get a soft
   * halo and slightly larger radius so dense areas read at a glance, while
   * sparse groups stay light. Reading aid only — it re-weights emphasis, never
   * the underlying data.
   */
  densityMode?: boolean;
  /**
   * technology_group_id → normalized patent-count weight (0–1) for density-mode
   * emphasis. Built by buildGroupDensityModel from the current filtered corpus.
   */
  groupWeight?: Map<number, number>;
}

const SVG_PADDING = 28;
const NODE_RADIUS_BASE = 4;
const NODE_RADIUS_MAX = 10;

// Tableau-style palette, used to color technology_group_id.
export const GROUP_COLORS = [
  "#1d3fbf",
  "#0f766e",
  "#b45309",
  "#7c3aed",
  "#be185d",
  "#0369a1",
  "#15803d",
  "#9f1239",
];

export function colorForGroup(groupId: number | null | undefined): string {
  if (groupId === null || groupId === undefined) return "#64748b";
  const idx =
    ((groupId % GROUP_COLORS.length) + GROUP_COLORS.length) %
    GROUP_COLORS.length;
  return GROUP_COLORS[idx];
}

interface LayoutNode extends LandscapeNode {
  cx: number;
  cy: number;
  r: number;
  color: string;
  visibleDegree: number;
}

interface LayoutEdge {
  source: LayoutNode;
  target: LayoutNode;
  strokeWidth: number;
  edge: LandscapeEdge;
}

interface Layout {
  width: number;
  height: number;
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  nodeById: Map<string, LayoutNode>;
  neighborsByNode: Map<string, Set<string>>;
}

function buildLayout(
  nodes: LandscapeNode[],
  edges: LandscapeEdge[],
  width: number,
  height: number,
): Layout {
  const empty: Layout = {
    width,
    height,
    nodes: [],
    edges: [],
    nodeById: new Map(),
    neighborsByNode: new Map(),
  };
  if (nodes.length === 0) return empty;

  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;

  const innerWidth = Math.max(0, width - SVG_PADDING * 2);
  const innerHeight = Math.max(0, height - SVG_PADDING * 2);

  const visibleNodeIds = new Set(nodes.map((n) => n.analysis_id));
  const visibleDegree = new Map<string, number>();
  for (const id of visibleNodeIds) visibleDegree.set(id, 0);
  for (const edge of edges) {
    if (
      visibleNodeIds.has(edge.source_analysis_id) &&
      visibleNodeIds.has(edge.target_analysis_id)
    ) {
      visibleDegree.set(
        edge.source_analysis_id,
        (visibleDegree.get(edge.source_analysis_id) ?? 0) + 1,
      );
      visibleDegree.set(
        edge.target_analysis_id,
        (visibleDegree.get(edge.target_analysis_id) ?? 0) + 1,
      );
    }
  }

  const maxDegree = Math.max(
    1,
    ...Array.from(visibleDegree.values()),
    ...nodes.map((n) => n.degree),
  );

  const laidOut: LayoutNode[] = nodes.map((node) => {
    const cx = SVG_PADDING + ((node.x - minX) / rangeX) * innerWidth;
    const cy = SVG_PADDING + (1 - (node.y - minY) / rangeY) * innerHeight;
    const vDeg = visibleDegree.get(node.analysis_id) ?? 0;
    const sizeDegree = vDeg > 0 ? vDeg : node.degree;
    const degreeRatio = sizeDegree / maxDegree;
    const r =
      NODE_RADIUS_BASE +
      Math.round(degreeRatio * (NODE_RADIUS_MAX - NODE_RADIUS_BASE));
    return {
      ...node,
      cx,
      cy,
      r,
      color: colorForGroup(node.technology_group_id),
      visibleDegree: vDeg,
    };
  });

  const nodeById = new Map<string, LayoutNode>();
  for (const node of laidOut) nodeById.set(node.analysis_id, node);

  const neighborsByNode = new Map<string, Set<string>>();
  const laidOutEdges: LayoutEdge[] = [];
  for (const edge of edges) {
    const source = nodeById.get(edge.source_analysis_id);
    const target = nodeById.get(edge.target_analysis_id);
    if (!source || !target) continue;
    const strength = Math.max(0, Math.min(1, edge.similarity_score));
    laidOutEdges.push({
      source,
      target,
      strokeWidth: 0.6 + strength * 1.8,
      edge,
    });
    if (!neighborsByNode.has(source.analysis_id))
      neighborsByNode.set(source.analysis_id, new Set());
    if (!neighborsByNode.has(target.analysis_id))
      neighborsByNode.set(target.analysis_id, new Set());
    neighborsByNode.get(source.analysis_id)!.add(target.analysis_id);
    neighborsByNode.get(target.analysis_id)!.add(source.analysis_id);
  }

  return {
    width,
    height,
    nodes: laidOut,
    edges: laidOutEdges,
    nodeById,
    neighborsByNode,
  };
}

export function LandscapeMiniGraph({
  data,
  height = 460,
  edges,
  visibleNodeIds,
  selectedId,
  hoveredId,
  onHoverNode,
  onSelectNode,
  onOpenNode,
  className,
  ariaLabel = "Landscape relationship network preview",
  caption,
  interactive = true,
  densityMode = false,
  groupWeight,
}: LandscapeMiniGraphProps) {
  const width = 760;
  const graphClassName = [
    "landscape-graph",
    interactive ? null : "landscape-graph--static",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  const resolvedCaption =
    caption === undefined ? (
      <>
        Hover a patent to preview its relationship neighborhood. Click to select
        it and open the preview panel. Double-click — or press <kbd>O</kbd>{" "}
        while focused — to open the Patent Dossier.
      </>
    ) : (
      caption
    );

  const visibleNodes = useMemo(() => {
    if (!visibleNodeIds) return data.nodes;
    return data.nodes.filter((node) => visibleNodeIds.has(node.analysis_id));
  }, [data.nodes, visibleNodeIds]);

  const activeEdges = useMemo(() => {
    const source = edges ?? data.edges;
    if (!visibleNodeIds) return source;
    return source.filter(
      (edge) =>
        visibleNodeIds.has(edge.source_analysis_id) &&
        visibleNodeIds.has(edge.target_analysis_id),
    );
  }, [edges, data.edges, visibleNodeIds]);

  const layout = useMemo(
    () => buildLayout(visibleNodes, activeEdges, width, height),
    [visibleNodes, activeEdges, height],
  );

  const focusId = hoveredId ?? selectedId ?? null;
  const hasFocus = focusId !== null && layout.nodeById.has(focusId);
  const focusNeighbors = hasFocus
    ? layout.neighborsByNode.get(focusId!) ?? new Set<string>()
    : new Set<string>();

  const svgRef = useRef<SVGSVGElement | null>(null);

  if (layout.nodes.length === 0) {
    return (
      <div className="landscape-graph__empty" role="status">
        <p className="card__muted" style={{ margin: 0 }}>
          No patents match the current filters. Loosen the relationship
          strength threshold or include more technology groups.
        </p>
      </div>
    );
  }

  const isNodeInFocus = (id: string): boolean => {
    if (!hasFocus) return true;
    return id === focusId || focusNeighbors.has(id);
  };

  const isEdgeInFocus = (e: LayoutEdge): boolean => {
    if (!hasFocus) return true;
    return (
      e.source.analysis_id === focusId || e.target.analysis_id === focusId
    );
  };

  const handleBackgroundClick = (event: React.MouseEvent) => {
    if (event.target === svgRef.current) {
      onSelectNode?.(null);
    }
  };

  return (
    <div className={graphClassName}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        preserveAspectRatio="xMidYMid meet"
        role={interactive ? "group" : "img"}
        aria-label={ariaLabel}
        className="landscape-graph__svg"
        onMouseLeave={() => onHoverNode?.(null)}
        onClick={handleBackgroundClick}
      >
        <defs>
          <pattern
            id="landscape-grid"
            width="40"
            height="40"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="rgba(15, 23, 42, 0.04)"
              strokeWidth="1"
            />
          </pattern>
        </defs>
        <rect
          x="0"
          y="0"
          width={layout.width}
          height={layout.height}
          fill="url(#landscape-grid)"
        />
        {densityMode && (
          <g className="landscape-graph__halos" aria-hidden="true">
            {layout.nodes.map((node) => {
              const weight =
                node.technology_group_id !== null
                  ? groupWeight?.get(node.technology_group_id) ?? 0
                  : 0;
              if (weight <= 0) return null;
              const inFocus = isNodeInFocus(node.analysis_id);
              const haloRadius = node.r + 5 + weight * 16;
              return (
                <circle
                  key={`halo-${node.analysis_id}`}
                  cx={node.cx}
                  cy={node.cy}
                  r={haloRadius}
                  fill={node.color}
                  opacity={(hasFocus && !inFocus ? 0.04 : 0.16) * (0.4 + weight)}
                  className="landscape-graph__halo"
                />
              );
            })}
          </g>
        )}
        <g className="landscape-graph__edges">
          {layout.edges.map((edge, idx) => {
            const inFocus = isEdgeInFocus(edge);
            const baseOpacity =
              0.22 + Math.max(0, Math.min(1, edge.edge.similarity_score)) * 0.5;
            const opacity = hasFocus
              ? inFocus
                ? Math.min(1, baseOpacity + 0.35)
                : 0.06
              : baseOpacity;
            const stroke = hasFocus && inFocus ? "#0f172a" : "#475569";
            const strokeWidth = hasFocus && inFocus
              ? edge.strokeWidth + 0.6
              : edge.strokeWidth;
            return (
              <line
                key={`${edge.source.analysis_id}->${edge.target.analysis_id}-${idx}`}
                x1={edge.source.cx}
                y1={edge.source.cy}
                x2={edge.target.cx}
                y2={edge.target.cy}
                stroke={stroke}
                strokeWidth={strokeWidth}
                opacity={opacity}
                strokeLinecap="round"
                className={`landscape-graph__edge${
                  hasFocus && inFocus ? " landscape-graph__edge--focus" : ""
                }${hasFocus && !inFocus ? " landscape-graph__edge--faded" : ""}`}
              >
                <title>
                  {edge.edge.relationship_strength} similarity (
                  {edge.edge.similarity_score.toFixed(3)})
                </title>
              </line>
            );
          })}
        </g>
        <g className="landscape-graph__nodes">
          {layout.nodes.map((node) => {
            const isSelected = node.analysis_id === selectedId;
            const isHovered = node.analysis_id === hoveredId;
            const inFocus = isNodeInFocus(node.analysis_id);
            const opacity = hasFocus ? (inFocus ? 1 : 0.18) : 0.92;
            const isPrimary = node.analysis_id === focusId;
            const stroke = isSelected
              ? "#0f172a"
              : isHovered
              ? "#0f172a"
              : "#ffffff";
            const strokeWidth = isSelected ? 2.8 : isHovered ? 2.2 : 1.5;
            const densityBoost =
              densityMode && node.technology_group_id !== null
                ? Math.round((groupWeight?.get(node.technology_group_id) ?? 0) * 3)
                : 0;
            const radius = (isPrimary ? node.r + 2 : node.r) + densityBoost;
            return (
              <circle
                key={node.analysis_id}
                cx={node.cx}
                cy={node.cy}
                r={radius}
                fill={node.color}
                fillOpacity={opacity}
                stroke={stroke}
                strokeWidth={strokeWidth}
                className={`landscape-graph__node${
                  isSelected ? " landscape-graph__node--selected" : ""
                }${isHovered ? " landscape-graph__node--hovered" : ""}${
                  hasFocus && !inFocus ? " landscape-graph__node--faded" : ""
                }`}
                tabIndex={interactive ? 0 : undefined}
                role={interactive ? "button" : undefined}
                aria-label={
                  interactive ? `Select ${node.title || node.patent_id}` : undefined
                }
                aria-pressed={interactive ? isSelected : undefined}
                onMouseEnter={
                  interactive ? () => onHoverNode?.(node.analysis_id) : undefined
                }
                onMouseLeave={interactive ? () => onHoverNode?.(null) : undefined}
                onFocus={
                  interactive ? () => onHoverNode?.(node.analysis_id) : undefined
                }
                onBlur={interactive ? () => onHoverNode?.(null) : undefined}
                onClick={
                  interactive
                    ? (event) => {
                        event.stopPropagation();
                        onSelectNode?.(node.analysis_id);
                      }
                    : undefined
                }
                onDoubleClick={
                  interactive
                    ? (event) => {
                        event.stopPropagation();
                        onOpenNode?.(node.analysis_id);
                      }
                    : undefined
                }
                onKeyDown={
                  interactive
                    ? (event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelectNode?.(node.analysis_id);
                        } else if (event.key === "o" || event.key === "O") {
                          event.preventDefault();
                          onOpenNode?.(node.analysis_id);
                        } else if (event.key === "Escape") {
                          event.preventDefault();
                          onSelectNode?.(null);
                        }
                      }
                    : undefined
                }
              >
                <title>
                  {(node.title || node.patent_id)} — {node.technology_group}
                  {node.assignee ? ` · ${node.assignee}` : ""}
                </title>
              </circle>
            );
          })}
        </g>
      </svg>
      {resolvedCaption !== null && (
        <p className="landscape-graph__caption">{resolvedCaption}</p>
      )}
    </div>
  );
}
