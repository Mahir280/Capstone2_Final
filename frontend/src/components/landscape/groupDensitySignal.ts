import type { LandscapeTechnologyGroup } from "../../types/landscape";

// Density and sparseness signals are derived from `patent_count` in the current
// filtered corpus view. They are used for the
// Crowded / Sparse badges, the white-space legend, and the density-mode halos on
// the graph. This is an exploratory reading aid over loaded data — not a market
// or patent-office conclusion.

export type GroupDensityTier = "crowded" | "typical" | "sparse";

export interface GroupDensitySignal {
  tier: GroupDensityTier;
  // patent_count normalized against the largest group (0–1), for graph emphasis.
  weight: number;
}

const CROWDED_SHARE = 0.66;
const SPARSE_SHARE = 0.33;

export interface GroupDensityModel {
  byGroupId: Map<number, GroupDensitySignal>;
  maxCount: number;
  crowdedCount: number;
  sparseCount: number;
}

// Classify each group relative to the densest group in view: groups at or above
// 66% of the max are "crowded", at or below 33% are "sparse", the rest typical.
// A single-group corpus is treated as typical (no relative signal to read).
export function buildGroupDensityModel(
  groups: LandscapeTechnologyGroup[],
): GroupDensityModel {
  const maxCount = groups.reduce(
    (acc, g) => (g.patent_count > acc ? g.patent_count : acc),
    0,
  );
  const byGroupId = new Map<number, GroupDensitySignal>();
  let crowdedCount = 0;
  let sparseCount = 0;

  for (const group of groups) {
    const weight = maxCount > 0 ? group.patent_count / maxCount : 0;
    let tier: GroupDensityTier = "typical";
    if (groups.length > 1 && maxCount > 0) {
      if (weight >= CROWDED_SHARE) tier = "crowded";
      else if (weight <= SPARSE_SHARE) tier = "sparse";
    }
    if (tier === "crowded") crowdedCount += 1;
    if (tier === "sparse") sparseCount += 1;
    byGroupId.set(group.technology_group_id, { tier, weight });
  }

  return { byGroupId, maxCount, crowdedCount, sparseCount };
}

export const GROUP_DENSITY_BADGE: Record<
  GroupDensityTier,
  { label: string; variant: "warning" | "neutral" | "accent" } | null
> = {
  crowded: { label: "Crowded", variant: "warning" },
  typical: null,
  sparse: { label: "Sparse", variant: "accent" },
};
