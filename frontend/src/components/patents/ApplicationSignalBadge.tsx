import { Badge, type BadgeVariant } from "../common/Badge";

export type ApplicationSignalTier = "strong" | "moderate" | "early" | "unknown";

export interface ApplicationSignalInfo {
  tier: ApplicationSignalTier;
  label: string;
  variant: BadgeVariant;
  description: string;
}

const SIGNAL_INFO: Record<ApplicationSignalTier, ApplicationSignalInfo> = {
  strong: {
    tier: "strong",
    label: "Strong signal",
    variant: "success",
    description:
      "Multiple technical signals or related records support this area.",
  },
  moderate: {
    tier: "moderate",
    label: "Moderate signal",
    variant: "primary",
    description: "Some relevant evidence exists, but it is not dominant.",
  },
  early: {
    tier: "early",
    label: "Early signal",
    variant: "warning",
    description:
      "Partial evidence only; useful as a reading aid for deeper review.",
  },
  unknown: {
    tier: "unknown",
    label: "Signal",
    variant: "neutral",
    description: "Signal strength was not reported for this area.",
  },
};

export function getApplicationSignalInfo(
  rawLevel: string | null | undefined,
): ApplicationSignalInfo {
  if (!rawLevel) return SIGNAL_INFO.unknown;
  const normalized = rawLevel.toLowerCase();
  if (normalized.includes("strong") || normalized.includes("high")) {
    return SIGNAL_INFO.strong;
  }
  if (normalized.includes("moderate") || normalized.includes("medium")) {
    return SIGNAL_INFO.moderate;
  }
  if (
    normalized.includes("early") ||
    normalized.includes("weak") ||
    normalized.includes("low")
  ) {
    return SIGNAL_INFO.early;
  }
  return SIGNAL_INFO.unknown;
}

interface ApplicationSignalBadgeProps {
  evidenceLevel: string | null | undefined;
  withDot?: boolean;
  showRawLevel?: boolean;
}

export function ApplicationSignalBadge({
  evidenceLevel,
  withDot = true,
  showRawLevel = false,
}: ApplicationSignalBadgeProps) {
  const info = getApplicationSignalInfo(evidenceLevel);
  return (
    <span
      className="application-signal-badge"
      title={info.description}
      aria-label={`${info.label}. ${info.description}`}
    >
      <Badge variant={info.variant} withDot={withDot}>
        {info.label}
      </Badge>
      {showRawLevel && evidenceLevel && (
        <span className="application-signal-badge__raw">({evidenceLevel})</span>
      )}
    </span>
  );
}

export const APPLICATION_SIGNAL_LEGEND: ApplicationSignalInfo[] = [
  SIGNAL_INFO.strong,
  SIGNAL_INFO.moderate,
  SIGNAL_INFO.early,
];
