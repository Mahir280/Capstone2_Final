import type {
  LandscapeEdge,
  LandscapeNode,
  LandscapeTechnologyGroup,
} from "../../types/landscape";
import {
  type OpportunitySignal,
  type OpportunitySignalTier,
  getCategoryLabel,
} from "./types";

const MAX_SIGNALS_PER_CATEGORY = 3;

interface LandscapeContext {
  groups: LandscapeTechnologyGroup[];
  visibleNodes: LandscapeNode[];
  filteredEdges: LandscapeEdge[];
}

function normalize(value: string): string {
  return value.trim();
}

function tierFromShare(share: number): OpportunitySignalTier {
  if (share >= 0.75) return "strong";
  if (share >= 0.5) return "moderate";
  return "early";
}

function tierFromLowness(value: number, median: number): OpportunitySignalTier {
  if (median <= 0) return "early";
  const ratio = value / median;
  if (ratio <= 0.25) return "strong";
  if (ratio <= 0.5) return "moderate";
  return "early";
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

function lighterNeighborhoodSignals({
  groups,
  visibleNodes,
  filteredEdges,
}: LandscapeContext): OpportunitySignal[] {
  if (groups.length === 0) return [];
  const nodeGroupById = new Map<string, number | null>();
  for (const node of visibleNodes) {
    nodeGroupById.set(node.analysis_id, node.technology_group_id);
  }
  const internalEdges = new Map<number, number>();
  const patentsInGroup = new Map<number, number>();
  for (const node of visibleNodes) {
    if (node.technology_group_id === null) continue;
    patentsInGroup.set(
      node.technology_group_id,
      (patentsInGroup.get(node.technology_group_id) ?? 0) + 1,
    );
  }
  for (const edge of filteredEdges) {
    const sg = nodeGroupById.get(edge.source_analysis_id);
    const tg = nodeGroupById.get(edge.target_analysis_id);
    if (sg === undefined || tg === undefined) continue;
    if (sg !== null && tg !== null && sg === tg) {
      internalEdges.set(sg, (internalEdges.get(sg) ?? 0) + 1);
    }
  }
  const candidates = groups
    .map((group) => {
      const patents = patentsInGroup.get(group.technology_group_id) ?? 0;
      const internal = internalEdges.get(group.technology_group_id) ?? 0;
      const edgesPerPatent = patents > 0 ? internal / patents : 0;
      return { group, patents, internal, edgesPerPatent };
    })
    .filter((c) => c.patents >= 2 && c.edgesPerPatent < 0.5)
    .sort((a, b) => a.edgesPerPatent - b.edgesPerPatent)
    .slice(0, MAX_SIGNALS_PER_CATEGORY);

  return candidates.map((c) => {
    const tier: OpportunitySignalTier =
      c.edgesPerPatent <= 0.1
        ? "strong"
        : c.edgesPerPatent <= 0.3
        ? "moderate"
        : "early";
    const title = c.group.group_label || c.group.technology_group;
    const evidence = [
      { label: "Patents in view", value: String(c.patents) },
      { label: "Internal relationships", value: String(c.internal) },
      {
        label: "Relationships per patent",
        value: c.edgesPerPatent.toFixed(2),
      },
    ];
    if (c.group.top_terms.length > 0) {
      evidence.push({
        label: "Top terms",
        value: c.group.top_terms.slice(0, 4).join(", "),
      });
    }
    return {
      id: `lighter-neighborhood-${c.group.technology_group_id}`,
      category: "lighter-neighborhood",
      categoryLabel: getCategoryLabel("lighter-neighborhood"),
      tier,
      title: `${title} appears as a lighter-density relationship neighborhood.`,
      rationale:
        "Few internal relationships per patent at the current threshold.",
      evidence,
      limitations: [],
    } satisfies OpportunitySignal;
  });
}

function lowDensityAreaSignals({
  visibleNodes,
}: LandscapeContext): OpportunitySignal[] {
  if (visibleNodes.length === 0) return [];
  const areaCounts = new Map<string, number>();
  const areaGroups = new Map<string, Set<string>>();
  for (const node of visibleNodes) {
    for (const rawArea of node.candidate_application_areas) {
      const area = normalize(rawArea);
      if (!area) continue;
      areaCounts.set(area, (areaCounts.get(area) ?? 0) + 1);
      if (!areaGroups.has(area)) areaGroups.set(area, new Set());
      if (node.technology_group) {
        areaGroups.get(area)!.add(node.technology_group);
      }
    }
  }
  if (areaCounts.size === 0) return [];
  const counts = Array.from(areaCounts.values());
  const med = median(counts);
  const threshold = Math.max(2, Math.floor(med / 2) || 1);
  const candidates = Array.from(areaCounts.entries())
    .filter(([, count]) => count > 0 && count <= threshold)
    .sort((a, b) => a[1] - b[1])
    .slice(0, MAX_SIGNALS_PER_CATEGORY);

  return candidates.map(([area, count]) => {
    const tier = tierFromLowness(count, med);
    const groupsCount = areaGroups.get(area)?.size ?? 0;
    const evidence = [
      { label: "Patents listing this area", value: String(count) },
      { label: "Corpus median per area", value: med.toFixed(1) },
    ];
    if (groupsCount > 0) {
      evidence.push({
        label: "Technology groups touching this area",
        value: String(groupsCount),
      });
    }
    return {
      id: `low-density-area-${area.toLowerCase()}`,
      category: "low-density-area",
      categoryLabel: getCategoryLabel("low-density-area"),
      tier,
      title: `${area} appears as a low-density application neighborhood.`,
      rationale:
        "Few visible patents list this candidate application area.",
      evidence,
      limitations: [],
    } satisfies OpportunitySignal;
  });
}

function assigneeConcentrationSignals({
  groups,
  visibleNodes,
}: LandscapeContext): OpportunitySignal[] {
  if (groups.length === 0) return [];
  const assigneesByGroup = new Map<number, Map<string, number>>();
  for (const node of visibleNodes) {
    if (node.technology_group_id === null) continue;
    const assignee = node.assignee?.trim();
    if (!assignee) continue;
    if (!assigneesByGroup.has(node.technology_group_id)) {
      assigneesByGroup.set(node.technology_group_id, new Map());
    }
    const bucket = assigneesByGroup.get(node.technology_group_id)!;
    bucket.set(assignee, (bucket.get(assignee) ?? 0) + 1);
  }
  const candidates: Array<{
    group: LandscapeTechnologyGroup;
    topAssignee: string;
    topCount: number;
    totalWithAssignee: number;
    distinctAssignees: number;
    share: number;
  }> = [];
  for (const group of groups) {
    const bucket = assigneesByGroup.get(group.technology_group_id);
    if (!bucket || bucket.size === 0) continue;
    let topAssignee = "";
    let topCount = 0;
    let totalWithAssignee = 0;
    for (const [assignee, count] of bucket.entries()) {
      totalWithAssignee += count;
      if (count > topCount) {
        topCount = count;
        topAssignee = assignee;
      }
    }
    if (totalWithAssignee < 3) continue;
    const share = topCount / totalWithAssignee;
    if (share < 0.5) continue;
    candidates.push({
      group,
      topAssignee,
      topCount,
      totalWithAssignee,
      distinctAssignees: bucket.size,
      share,
    });
  }
  candidates.sort((a, b) => b.share - a.share);
  return candidates.slice(0, MAX_SIGNALS_PER_CATEGORY).map((c) => {
    const tier = tierFromShare(c.share);
    const title = c.group.group_label || c.group.technology_group;
    const evidence = [
      {
        label: "Top assignee in group",
        value: `${c.topAssignee} (${c.topCount} / ${c.totalWithAssignee})`,
      },
      {
        label: "Top-assignee share",
        value: `${Math.round(c.share * 100)}%`,
      },
      {
        label: "Distinct assignees in view",
        value: String(c.distinctAssignees),
      },
    ];
    return {
      id: `assignee-concentration-${c.group.technology_group_id}`,
      category: "assignee-concentration",
      categoryLabel: getCategoryLabel("assignee-concentration"),
      tier,
      title: `${title} shows concentrated assignee activity.`,
      rationale:
        "Most visible patents in this group come from one organization.",
      evidence,
      limitations: [],
    } satisfies OpportunitySignal;
  });
}

function crossOverSignals({
  visibleNodes,
}: LandscapeContext): OpportunitySignal[] {
  if (visibleNodes.length === 0) return [];
  const pairCounts = new Map<
    string,
    { a: string; b: string; count: number }
  >();
  for (const node of visibleNodes) {
    const unique = Array.from(
      new Set(
        node.candidate_application_areas
          .map((a) => normalize(a))
          .filter((a) => a.length > 0),
      ),
    );
    for (let i = 0; i < unique.length; i++) {
      for (let j = i + 1; j < unique.length; j++) {
        const left = unique[i] < unique[j] ? unique[i] : unique[j];
        const right = unique[i] < unique[j] ? unique[j] : unique[i];
        const key = `${left}|||${right}`;
        const existing = pairCounts.get(key);
        if (existing) {
          existing.count += 1;
        } else {
          pairCounts.set(key, { a: left, b: right, count: 1 });
        }
      }
    }
  }
  if (pairCounts.size === 0) return [];
  const candidates = Array.from(pairCounts.values())
    .filter((entry) => entry.count >= 1 && entry.count <= 2)
    .sort((x, y) => x.count - y.count)
    .slice(0, MAX_SIGNALS_PER_CATEGORY);
  return candidates.map(({ a, b, count }) => {
    const tier: OpportunitySignalTier = count === 1 ? "moderate" : "early";
    const evidence = [
      { label: "Areas paired", value: `${a} × ${b}` },
      { label: "Patents combining both", value: String(count) },
    ];
    return {
      id: `cross-over-${a.toLowerCase()}-${b.toLowerCase()}`,
      category: "cross-over",
      categoryLabel: getCategoryLabel("cross-over"),
      tier,
      title: `${a} × ${b} appears as a cross-over area for review.`,
      rationale:
        "This candidate-area pair is rare in the current corpus.",
      evidence,
      limitations: [],
    } satisfies OpportunitySignal;
  });
}

export function buildLandscapeOpportunitySignals(
  context: LandscapeContext,
): OpportunitySignal[] {
  return [
    ...lighterNeighborhoodSignals(context),
    ...lowDensityAreaSignals(context),
    ...assigneeConcentrationSignals(context),
    ...crossOverSignals(context),
  ];
}
