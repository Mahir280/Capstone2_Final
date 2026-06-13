import { Badge, type BadgeVariant } from "../common/Badge";

export type RelationshipTier = "strong" | "moderate" | "early" | "unknown";

interface TierInfo {
  tier: RelationshipTier;
  label: string;
  variant: BadgeVariant;
  description: string;
}

const TIER_INFO: Record<RelationshipTier, TierInfo> = {
  strong: {
    tier: "strong",
    label: "Strong relationship",
    variant: "success",
    description:
      "High text-vector similarity, often supported by shared technical signals.",
  },
  moderate: {
    tier: "moderate",
    label: "Moderate relationship",
    variant: "primary",
    description:
      "Notable similarity, useful for context but not dominant evidence.",
  },
  early: {
    tier: "early",
    label: "Early relationship signal",
    variant: "warning",
    description:
      "Limited overlap — useful as a reading aid for deeper review.",
  },
  unknown: {
    tier: "unknown",
    label: "Relationship signal",
    variant: "neutral",
    description: "Relationship signal information was not provided.",
  },
};

export function classifyRelationshipTier(
  label: string | null | undefined,
  score?: number | null,
): RelationshipTier {
  const normalized = (label ?? "").toLowerCase();
  if (normalized.includes("strong") || normalized.includes("high")) return "strong";
  if (normalized.includes("moderate") || normalized.includes("medium")) return "moderate";
  if (
    normalized.includes("early") ||
    normalized.includes("weak") ||
    normalized.includes("low")
  ) {
    return "early";
  }
  if (typeof score === "number" && !Number.isNaN(score)) {
    if (score >= 0.65) return "strong";
    if (score >= 0.35) return "moderate";
    return "early";
  }
  return "unknown";
}

export function getRelationshipTierInfo(
  label: string | null | undefined,
  score?: number | null,
): TierInfo {
  return TIER_INFO[classifyRelationshipTier(label, score)];
}

function clampPct(score: number | null | undefined): number {
  if (score === null || score === undefined || Number.isNaN(score)) return 0;
  if (score <= 0) return 0;
  if (score >= 1) return 100;
  return Math.round(score * 100);
}

interface RelationshipStrengthMeterProps {
  label: string;
  score: number | null | undefined;
  caption?: string;
  compact?: boolean;
}

export function RelationshipStrengthMeter({
  label,
  score,
  caption,
  compact = false,
}: RelationshipStrengthMeterProps) {
  const info = getRelationshipTierInfo(label, score);
  const pct = clampPct(score);
  const scoreText = typeof score === "number" ? score.toFixed(2) : "—";

  return (
    <div
      className={`strength-meter strength-meter--${info.tier} ${
        compact ? "strength-meter--compact" : ""
      }`.trim()}
      role="group"
      aria-label={`${info.label} — score ${scoreText}`}
    >
      <div className="strength-meter__head">
        <Badge variant={info.variant} withDot>
          {info.label}
        </Badge>
        <span className="strength-meter__raw" title={info.description}>
          {label || "—"}
          <span className="strength-meter__score">· {scoreText}</span>
        </span>
      </div>
      <div
        className={`strength-meter__track strength-meter__track--${info.tier}`}
        aria-hidden="true"
      >
        <span
          className="strength-meter__fill"
          style={{ width: `${pct}%` }}
        />
      </div>
      {caption && <p className="strength-meter__caption">{caption}</p>}
    </div>
  );
}
