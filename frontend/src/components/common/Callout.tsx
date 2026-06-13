import type { ReactNode } from "react";

export type CalloutVariant =
  | "info"
  | "warning"
  | "error"
  | "success"
  | "neutral";

interface CalloutProps {
  variant?: CalloutVariant;
  title?: ReactNode;
  icon?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
  role?: "status" | "alert" | "note";
}

const DEFAULT_ICONS: Record<CalloutVariant, string> = {
  info: "i",
  warning: "!",
  error: "!",
  success: "✓",
  neutral: "•",
};

export function Callout({
  variant = "neutral",
  title,
  icon,
  children,
  actions,
  role,
}: CalloutProps) {
  const resolvedRole =
    role ??
    (variant === "error" ? "alert" : variant === "warning" ? "status" : "note");
  return (
    <div className={`callout callout--${variant}`} role={resolvedRole}>
      <div className="callout__icon" aria-hidden="true">
        {icon ?? DEFAULT_ICONS[variant]}
      </div>
      <div className="callout__body">
        {title && <span className="callout__title">{title}</span>}
        {children && <div className="callout__text">{children}</div>}
        {actions && <div className="callout__actions">{actions}</div>}
      </div>
    </div>
  );
}
