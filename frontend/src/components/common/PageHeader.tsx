import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  breadcrumb?: ReactNode;
  actions?: ReactNode;
  meta?: ReactNode;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  breadcrumb,
  actions,
  meta,
}: PageHeaderProps) {
  return (
    <header className="page-header">
      {breadcrumb && (
        <div className="page-header__breadcrumb">{breadcrumb}</div>
      )}
      <div className="page-header__top">
        <div className="page-header__main">
          {eyebrow && <span className="page-header__eyebrow">{eyebrow}</span>}
          <h1>{title}</h1>
          {description && (
            <p className="page-header__subtitle">{description}</p>
          )}
        </div>
        {actions && <div className="page-header__actions">{actions}</div>}
      </div>
      {meta && <div className="page-header__meta">{meta}</div>}
    </header>
  );
}
