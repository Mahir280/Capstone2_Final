import { useMemo } from "react";

import { SectionCard } from "../common/SectionCard";
import { colorForGroup } from "./LandscapeMiniGraph";
import type {
  LandscapeEdge,
  LandscapeNode,
  LandscapeTechnologyGroup,
} from "../../types/landscape";

type DensityTier = "crowded" | "moderate" | "lighter" | "single" | "empty";

interface GroupDensity {
  group: LandscapeTechnologyGroup;
  visiblePatents: number;
  visibleInternalEdges: number;
  visibleCrossEdges: number;
  edgesPerPatent: number;
  tier: DensityTier;
  tierLabel: string;
  tierDescription: string;
}

const TIER_LABELS: Record<DensityTier, { label: string; description: string }> = {
  crowded: {
    label: "Crowded",
    description:
      "Many visible relationships per patent.",
  },
  moderate: {
    label: "Moderate density",
    description:
      "Balanced visible relationships per patent.",
  },
  lighter: {
    label: "Lighter density",
    description:
      "Few visible relationships per patent.",
  },
  single: {
    label: "Single patent",
    description:
      "One visible patent at the current threshold.",
  },
  empty: {
    label: "No patents in view",
    description:
      "Hidden by current filters.",
  },
};

function classify(visiblePatents: number, edgesPerPatent: number): DensityTier {
  if (visiblePatents === 0) return "empty";
  if (visiblePatents === 1) return "single";
  if (edgesPerPatent >= 1.5) return "crowded";
  if (edgesPerPatent >= 0.5) return "moderate";
  return "lighter";
}

interface RelationshipDensityPanelProps {
  groups: LandscapeTechnologyGroup[];
  visibleNodes: LandscapeNode[];
  filteredEdges: LandscapeEdge[];
  isFocused: boolean;
}

export function RelationshipDensityPanel({
  groups,
  visibleNodes,
  filteredEdges,
  isFocused,
}: RelationshipDensityPanelProps) {
  const densities = useMemo<GroupDensity[]>(() => {
    if (groups.length === 0) return [];
    const nodeGroupById = new Map<string, number | null>();
    for (const node of visibleNodes) {
      nodeGroupById.set(node.analysis_id, node.technology_group_id);
    }
    const patentsPerGroup = new Map<number, number>();
    for (const node of visibleNodes) {
      if (node.technology_group_id === null) continue;
      patentsPerGroup.set(
        node.technology_group_id,
        (patentsPerGroup.get(node.technology_group_id) ?? 0) + 1,
      );
    }
    const internalPerGroup = new Map<number, number>();
    const crossPerGroup = new Map<number, number>();
    for (const edge of filteredEdges) {
      const sg = nodeGroupById.get(edge.source_analysis_id);
      const tg = nodeGroupById.get(edge.target_analysis_id);
      if (sg === undefined || tg === undefined) continue;
      if (sg === null && tg === null) continue;
      if (sg !== null && tg !== null && sg === tg) {
        internalPerGroup.set(sg, (internalPerGroup.get(sg) ?? 0) + 1);
      } else {
        if (sg !== null) {
          crossPerGroup.set(sg, (crossPerGroup.get(sg) ?? 0) + 1);
        }
        if (tg !== null) {
          crossPerGroup.set(tg, (crossPerGroup.get(tg) ?? 0) + 1);
        }
      }
    }
    return groups
      .map((group) => {
        const visiblePatents =
          patentsPerGroup.get(group.technology_group_id) ?? 0;
        const visibleInternalEdges =
          internalPerGroup.get(group.technology_group_id) ?? 0;
        const visibleCrossEdges =
          crossPerGroup.get(group.technology_group_id) ?? 0;
        const edgesPerPatent =
          visiblePatents > 0 ? visibleInternalEdges / visiblePatents : 0;
        const tier = classify(visiblePatents, edgesPerPatent);
        const meta = TIER_LABELS[tier];
        return {
          group,
          visiblePatents,
          visibleInternalEdges,
          visibleCrossEdges,
          edgesPerPatent,
          tier,
          tierLabel: meta.label,
          tierDescription: meta.description,
        } satisfies GroupDensity;
      })
      .sort((a, b) => {
        if (b.visibleInternalEdges !== a.visibleInternalEdges) {
          return b.visibleInternalEdges - a.visibleInternalEdges;
        }
        return b.visiblePatents - a.visiblePatents;
      });
  }, [groups, visibleNodes, filteredEdges]);

  if (groups.length === 0) {
    return null;
  }

  const crowded = densities.filter((d) => d.tier === "crowded").length;
  const lighter = densities.filter((d) => d.tier === "lighter").length;

  return (
    <SectionCard
      title="Relationship density"
      description={
        (isFocused
          ? "Per-group crowding inside the focused neighborhood."
          : "Per-group crowding in the visible map.") +
        " Crowded means ≥ 1.5 internal relationships per patent; moderate ≥ 0.5; lighter below that."
      }
    >
      <p className="density-panel__summary">
        <strong>{crowded}</strong> crowded · <strong>{lighter}</strong>{" "}
        lighter-density · <strong>{densities.length}</strong> groups tracked.
      </p>

      <ul className="density-panel__grid">
        {densities.map((entry) => (
          <li
            key={entry.group.technology_group_id}
            className={`density-card density-card--${entry.tier}`}
          >
            <div className="density-card__head">
              <span
                className="density-card__swatch"
                style={{
                  background: colorForGroup(entry.group.technology_group_id),
                }}
                aria-hidden="true"
              />
              <div className="density-card__heading">
                <span className="density-card__title">
                  {entry.group.group_label || entry.group.technology_group}
                </span>
                <span className="density-card__sub">
                  {entry.group.technology_group}
                </span>
              </div>
              <span
                className={`density-card__tier density-card__tier--${entry.tier}`}
                title={entry.tierDescription}
              >
                {entry.tierLabel}
              </span>
            </div>

            <dl className="density-card__stats">
              <div>
                <dt>Patents in view</dt>
                <dd>{entry.visiblePatents}</dd>
              </div>
              <div>
                <dt>Internal relationships</dt>
                <dd>{entry.visibleInternalEdges}</dd>
              </div>
              <div>
                <dt>Cross-group bridges</dt>
                <dd>{entry.visibleCrossEdges}</dd>
              </div>
              <div>
                <dt>Relationships / patent</dt>
                <dd>{entry.edgesPerPatent.toFixed(2)}</dd>
              </div>
            </dl>

            <div
              className={`density-card__bar density-card__bar--${entry.tier}`}
              aria-hidden="true"
            >
              <span
                className="density-card__bar-fill"
                style={{
                  width: `${Math.min(
                    100,
                    Math.round((entry.edgesPerPatent / 3) * 100),
                  )}%`,
                }}
              />
            </div>
            <p className="density-card__hint">{entry.tierDescription}</p>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}
