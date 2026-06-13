import type { ReactNode } from "react";

// A plain, accessible representation of a chart's underlying numbers. ECharts
// renders to a canvas that assistive technology cannot read, so key charts pair
// the canvas with one of these tables (either visually hidden as a screen-reader
// fallback, or shown via the ChartCard "view as table" toggle).
export interface ChartTableData {
  // Used as the <caption>; describes what the table contains.
  caption: string;
  // Header labels. columns[0] labels the row-header column.
  columns: string[];
  // One array per row. cells[0] becomes the row header; the rest are data cells.
  rows: Array<Array<ReactNode>>;
}

interface ChartDataTableProps {
  table: ChartTableData;
  // When true the table is present in the DOM for assistive tech but hidden
  // visually (the chart canvas remains the visible representation).
  visuallyHidden?: boolean;
}

export function ChartDataTable({ table, visuallyHidden }: ChartDataTableProps) {
  const wrapClass = visuallyHidden ? "visually-hidden" : "chart-data-table-wrap";
  return (
    <div className={wrapClass}>
      <table className="chart-data-table">
        <caption>{table.caption}</caption>
        <thead>
          <tr>
            {table.columns.map((column, index) => (
              <th
                key={column}
                scope="col"
                className={index === 0 ? undefined : "chart-data-table__num"}
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={String(row[0])}>
              {row.map((cell, cellIndex) =>
                cellIndex === 0 ? (
                  <th key="row-header" scope="row">
                    {cell}
                  </th>
                ) : (
                  <td key={cellIndex} className="chart-data-table__num">
                    {cell}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
