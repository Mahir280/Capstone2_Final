import type { ReactNode } from "react";

interface EmptyStateProps {
  title?: string;
  message: ReactNode;
  actions?: ReactNode;
}

export function EmptyState({
  title = "Nothing to show yet",
  message,
  actions,
}: EmptyStateProps) {
  return (
    <div className="callout callout--neutral" role="status">
      <div className="callout__icon" aria-hidden="true">
        ∅
      </div>
      <div className="callout__body">
        <span className="callout__title">{title}</span>
        <div className="callout__text">
          {typeof message === "string" ? <p>{message}</p> : message}
        </div>
        {actions && <div className="callout__actions">{actions}</div>}
      </div>
    </div>
  );
}
