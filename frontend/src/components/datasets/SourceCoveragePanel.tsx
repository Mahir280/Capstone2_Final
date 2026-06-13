import { SectionCard } from "../common/SectionCard";

interface SourceCoveragePanelProps {
  counts: Record<string, number>;
  total: number;
}

interface RepresentationRow {
  key: string;
  value: number;
  share: number;
  tier: "primary" | "supporting" | "trace";
  tierLabel: string;
}

function classify(share: number): {
  tier: "primary" | "supporting" | "trace";
  tierLabel: string;
} {
  if (share >= 0.4) return { tier: "primary", tierLabel: "Primary source" };
  if (share >= 0.1)
    return { tier: "supporting", tierLabel: "Supporting source" };
  return { tier: "trace", tierLabel: "Trace presence" };
}

export function SourceCoveragePanel({
  counts,
  total,
}: SourceCoveragePanelProps) {
  const entries = Object.entries(counts)
    .filter(([, value]) => value > 0)
    .sort((a, b) => b[1] - a[1]);

  if (entries.length === 0) {
    return (
      <SectionCard
        title="Source authority coverage"
        description="No source-authority breakdown available."
      >
        <p className="card__muted">
          Load a curated source-labeled corpus to populate this panel.
        </p>
      </SectionCard>
    );
  }

  const rows: RepresentationRow[] = entries.map(([key, value]) => {
    const share = total > 0 ? value / total : 0;
    const { tier, tierLabel } = classify(share);
    return { key, value, share, tier, tierLabel };
  });

  return (
    <SectionCard
      title="Source authority coverage"
      description="Source-authority mix in the loaded corpus."
    >
      <ul className="source-coverage">
        {rows.map((row) => {
          const pct = Math.round(row.share * 100);
          return (
            <li
              key={row.key}
              className={`source-coverage__row source-coverage__row--${row.tier}`}
            >
              <div className="source-coverage__head">
                <span className="source-coverage__name">{row.key}</span>
                <span
                  className={`source-coverage__tier source-coverage__tier--${row.tier}`}
                >
                  {row.tierLabel}
                </span>
              </div>
              <div className="source-coverage__meta">
                <span className="source-coverage__count">
                  {row.value} record{row.value === 1 ? "" : "s"}
                </span>
                <span className="source-coverage__share">{pct}%</span>
              </div>
              <div
                className={`source-coverage__bar source-coverage__bar--${row.tier}`}
                aria-hidden="true"
              >
                <span
                  className="source-coverage__bar-fill"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </SectionCard>
  );
}
