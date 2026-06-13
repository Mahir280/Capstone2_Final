import type { BadgeVariant } from "../common/Badge";

export type OpportunitySignalTier = "strong" | "moderate" | "early";

export type OpportunitySignalCategory =
  | "low-density-area"
  | "lighter-neighborhood"
  | "assignee-concentration"
  | "cross-over"
  | "emerging";

export interface OpportunitySignalEvidence {
  label: string;
  value: string;
}

export interface OpportunitySignal {
  id: string;
  category: OpportunitySignalCategory;
  categoryLabel: string;
  tier: OpportunitySignalTier;
  title: string;
  rationale: string;
  evidence: OpportunitySignalEvidence[];
  limitations: string[];
}

interface TierMeta {
  label: string;
  variant: BadgeVariant;
  description: string;
}

const TIER_META: Record<OpportunitySignalTier, TierMeta> = {
  strong: {
    label: "Strong review signal",
    variant: "success",
    description: "Multiple corpus-level indicators agree.",
  },
  moderate: {
    label: "Moderate review signal",
    variant: "primary",
    description: "Some corpus-level indicators agree.",
  },
  early: {
    label: "Early review signal",
    variant: "warning",
    description: "Limited corpus evidence.",
  },
};

export function getSignalTierMeta(tier: OpportunitySignalTier): TierMeta {
  return TIER_META[tier];
}

const CATEGORY_LABELS: Record<OpportunitySignalCategory, string> = {
  "low-density-area": "Low-density application area",
  "lighter-neighborhood": "Lighter-density technology group",
  "assignee-concentration": "Concentrated-assignee area",
  "cross-over": "Cross-over area for review",
  emerging: "Emerging area for deeper review",
};

export function getCategoryLabel(category: OpportunitySignalCategory): string {
  return CATEGORY_LABELS[category];
}

// Shared caveats live once at the panel level (OpportunitySignalsPanel's
// callout) instead of repeating on every card; `limitations` remains for
// card-specific caveats only.
