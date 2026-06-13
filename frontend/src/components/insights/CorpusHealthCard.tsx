import { ChartCard } from "../charts";
import type { AnalyticsResponse } from "../../types/analytics";

// Compact, filter-aware corpus health summary. Unlike the raw completeness bars
// elsewhere on the Data Quality tab, these are interpretive coverage notes:
// corpus size, source-authority skew, year span, and assignee coverage, read
// against the records currently in view rather than the whole store.

type HealthTier = "good" | "watch" | "limited";

const TIER_LABELS: Record<HealthTier, string> = {
  good: "Healthy",
  watch: "Watch",
  limited: "Limited",
};

interface HealthNote {
  key: string;
  tier: HealthTier;
  title: string;
  detail: string;
}

function topShare(
  counts: Record<string, number>,
): { key: string; share: number } | null {
  let topKey: string | null = null;
  let topValue = 0;
  let total = 0;
  for (const [key, value] of Object.entries(counts)) {
    if (value <= 0) continue;
    total += value;
    if (value > topValue) {
      topValue = value;
      topKey = key;
    }
  }
  if (!topKey || total === 0) return null;
  return { key: topKey, share: topValue / total };
}

function corpusSizeNote(n: number): HealthNote {
  if (n >= 200) {
    return {
      key: "corpus-size",
      tier: "good",
      title: "Records in view",
      detail: `${n} records in view — broad enough for trend, assignee, and technology reading.`,
    };
  }
  if (n >= 50) {
    return {
      key: "corpus-size",
      tier: "watch",
      title: "Records in view",
      detail: `${n} records in view — usable for exploration, but pattern signals will be sparser.`,
    };
  }
  return {
    key: "corpus-size",
    tier: "limited",
    title: "Records in view",
    detail: `${n} records in view — small slice, treat trend signals as early reading aids only.`,
  };
}

function sourceBalanceNote(data: AnalyticsResponse): HealthNote | null {
  const top = topShare(data.corpus.by_source);
  if (!top) return null;
  const pct = Math.round(top.share * 100);
  if (top.share >= 0.85) {
    return {
      key: "source-balance",
      tier: "limited",
      title: "Source authority balance",
      detail: `${top.key} dominates ${pct}% of records in view — coverage skews to one authority, so cross-authority comparison is limited.`,
    };
  }
  if (top.share >= 0.6) {
    return {
      key: "source-balance",
      tier: "watch",
      title: "Source authority balance",
      detail: `${top.key} represents ${pct}% of records in view — keep this skew in mind when reading the charts.`,
    };
  }
  return {
    key: "source-balance",
    tier: "good",
    title: "Source authority balance",
    detail: `Records spread across multiple source authorities; the top authority is ${top.key} at ${pct}%.`,
  };
}

function yearCoverageNote(data: AnalyticsResponse): HealthNote | null {
  const years = Object.entries(data.trends.by_publication_year)
    .map(([year, count]) => ({ year: Number(year), count }))
    .filter((entry) => entry.count > 0 && Number.isFinite(entry.year))
    .sort((a, b) => a.year - b.year);
  if (years.length === 0) return null;
  const min = years[0].year;
  const max = years[years.length - 1].year;
  const span = max - min + 1;
  const distinct = years.length;
  const yearWord = distinct === 1 ? "year" : "years";
  if (span >= 10 && distinct >= span * 0.6) {
    return {
      key: "year-coverage",
      tier: "good",
      title: "Year coverage",
      detail: `Records span ${min}–${max} across ${distinct} distinct ${yearWord} — good range for trend reading.`,
    };
  }
  if (span >= 5) {
    return {
      key: "year-coverage",
      tier: "watch",
      title: "Year coverage",
      detail: `Records span ${min}–${max} (${distinct} ${yearWord}) — gaps may bias year-based trend reading.`,
    };
  }
  return {
    key: "year-coverage",
    tier: "limited",
    title: "Year coverage",
    detail: `Records cover only ${distinct} ${yearWord} (${min}–${max}) — read year-based trends as early signals only.`,
  };
}

function assigneeNote(data: AnalyticsResponse): HealthNote | null {
  const pct = data.quality.field_completeness_pct.assignee;
  if (typeof pct !== "number") return null;
  const total = data.total_records_after_filter;
  const recognized = Math.round((pct / 100) * total);
  const rounded = Math.round(pct);
  if (pct >= 70) {
    return {
      key: "assignee-recognition",
      tier: "good",
      title: "Assignee coverage",
      detail: `${recognized} of ${total} records in view (${rounded}%) carry a recorded assignee.`,
    };
  }
  if (pct >= 40) {
    return {
      key: "assignee-recognition",
      tier: "watch",
      title: "Assignee coverage",
      detail: `${recognized} of ${total} records in view (${rounded}%) carry a recorded assignee — read assignee charts as partial.`,
    };
  }
  return {
    key: "assignee-recognition",
    tier: "limited",
    title: "Assignee coverage",
    detail: `Only ${recognized} of ${total} records in view (${rounded}%) carry a recorded assignee — assignee charts may understate activity.`,
  };
}

function buildHealthNotes(data: AnalyticsResponse): HealthNote[] {
  const notes: HealthNote[] = [
    corpusSizeNote(data.total_records_after_filter),
  ];
  const source = sourceBalanceNote(data);
  if (source) notes.push(source);
  const year = yearCoverageNote(data);
  if (year) notes.push(year);
  const assignee = assigneeNote(data);
  if (assignee) notes.push(assignee);
  return notes;
}

interface CorpusHealthCardProps {
  data: AnalyticsResponse;
}

export function CorpusHealthCard({ data }: CorpusHealthCardProps) {
  const notes = buildHealthNotes(data);
  const limitedCount = notes.filter((n) => n.tier === "limited").length;
  const watchCount = notes.filter((n) => n.tier === "watch").length;
  const noRecords = data.total_records_after_filter === 0;

  return (
    <ChartCard
      title="Corpus health"
      description="Coverage notes for the records in view."
      className="analytics-grid__wide"
      isEmpty={noRecords}
      emptyMessage="No records match the active filter."
    >
      <p className="coverage-health__summary">
        <strong>{notes.length}</strong> coverage notes ·{" "}
        <strong>{limitedCount}</strong> limited · <strong>{watchCount}</strong>{" "}
        to watch. Curated corpus only.
      </p>
      <ul className="coverage-health__list">
        {notes.map((note) => (
          <li
            key={note.key}
            className={`coverage-health__row coverage-health__row--${note.tier}`}
          >
            <span
              className={`coverage-health__dot coverage-health__dot--${note.tier}`}
              aria-hidden="true"
            />
            <div className="coverage-health__body">
              <div className="coverage-health__row-head">
                <span className="coverage-health__title">{note.title}</span>
                <span
                  className={`coverage-health__tier coverage-health__tier--${note.tier}`}
                >
                  {TIER_LABELS[note.tier]}
                </span>
              </div>
              <p className="coverage-health__detail">{note.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </ChartCard>
  );
}
