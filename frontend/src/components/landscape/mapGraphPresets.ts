import type { LandscapeQuery } from "../../types/landscape";

// The Map's five graph-tuning parameters are driven by three human-readable
// presets, with an Advanced expander exposing the raw values. They stay local
// to the Map because they tune how the graph is drawn, not which corpus slice
// is in view.

export type GraphParamKey =
  | "relationship_threshold"
  | "top_k"
  | "technology_group_count"
  | "max_edges"
  | "min_application_score";

export type GraphParams = Record<GraphParamKey, number>;

export type PresetKey = "tighter" | "balanced" | "broader";

// Selection state: a named preset, or "custom" once the user edits a raw value
// in the Advanced expander (so the UI stops claiming a preset is active).
export type GraphSelection = PresetKey | "custom";

export interface PresetDefinition {
  key: PresetKey;
  label: string;
  description: string;
  params: GraphParams;
}

// Balanced reproduces today's default behavior exactly — these are the FastAPI
// /api/landscape query defaults (relationship_threshold=0.20, top_k=5,
// technology_group_count=7, max_edges=80, min_application_score=0.0). Verified
// against backend/api/routes/landscape.py. Tighter raises the relationship
// threshold and trims edges/neighbors for a sparser, higher-confidence read;
// Broader lowers the threshold and admits more edges/neighbors for a denser one.
// All presets share technology_group_count=7, the configuration the Genetic
// Algorithm validation run recommends for the canonical corpus (Method &
// Validation page) — presets tune link density, not the grouping itself.
export const MAP_PRESETS: Record<PresetKey, PresetDefinition> = {
  tighter: {
    key: "tighter",
    label: "Tighter",
    description: "Stronger links, fewer edges.",
    params: {
      relationship_threshold: 0.32,
      top_k: 3,
      technology_group_count: 7,
      max_edges: 50,
      min_application_score: 0,
    },
  },
  balanced: {
    key: "balanced",
    label: "Balanced",
    description: "Default coverage and clarity.",
    params: {
      relationship_threshold: 0.2,
      top_k: 5,
      technology_group_count: 7,
      max_edges: 80,
      min_application_score: 0,
    },
  },
  broader: {
    key: "broader",
    label: "Broader",
    description: "Weaker links, more edges.",
    params: {
      relationship_threshold: 0.1,
      top_k: 8,
      technology_group_count: 7,
      max_edges: 160,
      min_application_score: 0,
    },
  },
};

export const DEFAULT_PRESET: PresetKey = "balanced";

export const GRAPH_PARAM_META: Record<
  GraphParamKey,
  { label: string; min: number; max: number; step: number; hint: string }
> = {
  relationship_threshold: {
    label: "Relationship threshold",
    min: 0,
    max: 1,
    step: 0.01,
    hint: "Minimum cosine similarity (0–1) needed for a link.",
  },
  top_k: {
    label: "Neighbors per patent (top-k)",
    min: 1,
    max: 50,
    step: 1,
    hint: "Nearest neighbors per patent.",
  },
  technology_group_count: {
    label: "Technology groups",
    min: 2,
    max: 20,
    step: 1,
    hint: "Target number of technology groups (7 = GA-validated default).",
  },
  max_edges: {
    label: "Max relationships",
    min: 1,
    max: 2000,
    step: 10,
    hint: "Maximum visible relationships.",
  },
  min_application_score: {
    label: "Min application score",
    min: 0,
    max: 100,
    step: 1,
    hint: "Minimum score for candidate areas.",
  },
};

export const GRAPH_PARAM_ORDER: GraphParamKey[] = [
  "relationship_threshold",
  "top_k",
  "technology_group_count",
  "max_edges",
  "min_application_score",
];

// Identify which preset (if any) a raw param set corresponds to, so a custom
// override can be reflected as "custom" and an exact match snaps back to a chip.
export function matchPreset(params: GraphParams): GraphSelection {
  for (const def of Object.values(MAP_PRESETS)) {
    const same = GRAPH_PARAM_ORDER.every(
      (key) => def.params[key] === params[key],
    );
    if (same) return def.key;
  }
  return "custom";
}

// Merge the Map-local graph params onto a filter-spine query so getLandscape /
// getFocusedLandscape receive both the corpus filters and the graph tuning.
export function withGraphParams(
  filters: LandscapeQuery,
  params: GraphParams,
): LandscapeQuery {
  return { ...filters, ...params };
}
