import type { ReactNode } from "react";

export type BadgeVariant =
  | "neutral"
  | "primary"
  | "success"
  | "warning"
  | "error"
  | "accent";

interface BadgeProps {
  variant?: BadgeVariant;
  withDot?: boolean;
  children: ReactNode;
}

export function Badge({
  variant = "neutral",
  withDot = false,
  children,
}: BadgeProps) {
  return (
    <span className={`badge badge--${variant}`}>
      {withDot && <span className="badge__dot" aria-hidden="true" />}
      {children}
    </span>
  );
}
