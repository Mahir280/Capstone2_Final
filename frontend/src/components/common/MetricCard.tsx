import type { ReactNode } from "react";

export type MetricVariant =
  | "default"
  | "primary"
  | "accent"
  | "success"
  | "warning";

interface MetricCardProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  variant?: MetricVariant;
  compact?: boolean;
}

export function MetricCard({
  label,
  value,
  hint,
  variant = "default",
  compact = false,
}: MetricCardProps) {
  const classes = ["metric-card"];
  if (variant !== "default") classes.push(`metric-card--${variant}`);
  return (
    <div className={classes.join(" ")}>
      <div className="metric-card__label">{label}</div>
      <div
        className={
          compact ? "metric-card__value metric-card__value--sm" : "metric-card__value"
        }
      >
        {value}
      </div>
      {hint && <div className="metric-card__hint">{hint}</div>}
    </div>
  );
}
