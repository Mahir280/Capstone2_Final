import { useId, useState } from "react";
import type { ReactNode } from "react";

import { ChartDataTable, type ChartTableData } from "./ChartDataTable";

interface ChartCardProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  note?: ReactNode;
  isEmpty?: boolean;
  emptyMessage?: ReactNode;
  // Optional accessible data fallback for the chart. When provided, a
  // visually-hidden copy of the table is always rendered alongside the canvas
  // (so screen readers can reach the numbers), and a "View as table" toggle lets
  // sighted keyboard users swap the canvas for the visible table.
  table?: ChartTableData;
  className?: string;
  children: ReactNode;
}

export function ChartCard({
  title,
  description,
  actions,
  note,
  isEmpty = false,
  emptyMessage = "No data matches the current filters.",
  table,
  className,
  children,
}: ChartCardProps) {
  const headingId = useId();
  const descriptionId = useId();
  const [showTable, setShowTable] = useState(false);
  const classes = ["card", "chart-card", className].filter(Boolean).join(" ");
  const canToggleTable = Boolean(table) && !isEmpty;

  return (
    <section
      className={classes}
      role="group"
      aria-labelledby={headingId}
      aria-describedby={description ? descriptionId : undefined}
    >
      <header className="card__head">
        <div className="card__head-text">
          <h3 className="card__title" id={headingId}>
            {title}
          </h3>
          {description && (
            <p className="card__description" id={descriptionId}>
              {description}
            </p>
          )}
        </div>
        {(actions || canToggleTable) && (
          <div className="card__head-actions">
            {actions}
            {canToggleTable && (
              <button
                type="button"
                className="chart-card__table-toggle"
                aria-pressed={showTable}
                onClick={() => setShowTable((value) => !value)}
              >
                {showTable ? "View as chart" : "View as table"}
              </button>
            )}
          </div>
        )}
      </header>
      {isEmpty ? (
        <div className="chart-card__empty" role="status">
          <span className="chart-card__empty-icon" aria-hidden="true">
            ∅
          </span>
          <p>{emptyMessage}</p>
        </div>
      ) : table && showTable ? (
        <ChartDataTable table={table} />
      ) : (
        <>
          {children}
          {table && <ChartDataTable table={table} visuallyHidden />}
        </>
      )}
      {note && !isEmpty && <p className="chart-card__note">{note}</p>}
    </section>
  );
}
