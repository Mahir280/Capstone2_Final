import { Badge } from "../common/Badge";
import { StatTile } from "../common/StatTile";
import type { DataSourceStatusResponse } from "../../types/dataSources";

interface DatasetCoverageStatusProps {
  status: DataSourceStatusResponse;
  isLoading: boolean;
  onRefresh: () => void;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value);
}

function distinctKeys(record: Record<string, number>): number {
  return Object.keys(record).filter((key) => (record[key] ?? 0) > 0).length;
}

function activeImportMethod(
  record: Record<string, number>,
): { key: string; value: number } | null {
  let topKey: string | null = null;
  let topValue = 0;
  for (const [key, value] of Object.entries(record)) {
    if (value <= 0) continue;
    if (value > topValue) {
      topValue = value;
      topKey = key;
    }
  }
  return topKey ? { key: topKey, value: topValue } : null;
}

export function DatasetCoverageStatus({
  status,
  isLoading,
  onRefresh,
}: DatasetCoverageStatusProps) {
  const sourceAuthorityCount = distinctKeys(status.source_authority_counts);
  const importMethod = activeImportMethod(status.import_method_counts);
  const corpusBadge = status.has_patents ? (
    <Badge variant="success" withDot>
      Loaded
    </Badge>
  ) : (
    <Badge variant="warning" withDot>
      Not loaded
    </Badge>
  );

  return (
    <section
      className="coverage-status"
      role="region"
      aria-label="Corpus and source status"
    >
      <header className="coverage-status__head">
        <div className="coverage-status__heading">
          <span className="coverage-status__eyebrow">Current corpus</span>
          <h2 className="coverage-status__title">
            Curated source-labeled corpus
          </h2>
          <p className="coverage-status__intro">
            Powers Overview, Map, Trends & Players, Search, and dossiers.
            Coverage is bounded to the loaded local records.
          </p>
        </div>
        <div className="coverage-status__head-actions">
          {corpusBadge}
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={onRefresh}
            disabled={isLoading}
          >
            ⟳ Refresh corpus status
          </button>
        </div>
      </header>

      <div className="coverage-status__grid">
        <StatTile
          classNamePrefix="coverage-status"
          label="Loaded records"
          value={formatNumber(status.total_patents)}
          hint={
            status.has_patents
              ? "Available across corpus views."
              : "No records currently loaded into the local store."
          }
          primary
        />
        <StatTile
          classNamePrefix="coverage-status"
          label="Source authorities represented"
          value={formatNumber(sourceAuthorityCount)}
          hint="Distinct source-authority labels in the corpus."
        />
        <StatTile
          classNamePrefix="coverage-status"
          label="Year range"
          value={status.year_range || "—"}
          hint="Span of publication years observed."
        />
        <StatTile
          classNamePrefix="coverage-status"
          label="Recognized assignees"
          value={formatNumber(status.assignee_count)}
          hint="Distinct organizations with records."
        />
        <StatTile
          classNamePrefix="coverage-status"
          label="Active import mode"
          value={importMethod ? importMethod.key : "—"}
          hint={
            importMethod
              ? `${formatNumber(importMethod.value)} record${
                  importMethod.value === 1 ? "" : "s"
                } via this mode.`
              : "No import method has been recorded yet."
          }
        />
        <StatTile
          classNamePrefix="coverage-status"
          label="Local store file"
          value={status.database_exists ? "Present" : "Missing"}
          hint={
            <span
              className="coverage-status__hint--mono"
              title={status.database_path || undefined}
            >
              {status.database_path || "Path not reported"}
            </span>
          }
        />
      </div>
    </section>
  );
}
