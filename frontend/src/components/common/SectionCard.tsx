import type { ReactNode } from "react";

interface SectionCardProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function SectionCard({
  title,
  description,
  actions,
  children,
  className,
}: SectionCardProps) {
  const classes = ["card", className].filter(Boolean).join(" ");
  return (
    <section className={classes}>
      <header className="card__head">
        <div className="card__head-text">
          <h2 className="card__title">{title}</h2>
          {description && (
            <p className="card__description">{description}</p>
          )}
        </div>
        {actions && <div className="card__head-actions">{actions}</div>}
      </header>
      {children}
    </section>
  );
}
