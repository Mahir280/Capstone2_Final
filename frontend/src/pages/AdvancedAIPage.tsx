import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import { runAdvancedAIOptimization } from "../api/advancedAi";
import { Badge } from "../components/common/Badge";
import { Callout } from "../components/common/Callout";
import { DatasetWarningCallout } from "../components/common/DatasetWarningCallout";
import { ErrorState } from "../components/common/ErrorState";
import { MetricCard } from "../components/common/MetricCard";
import { PageHeader } from "../components/common/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import {
  ADVANCED_AI_DEFAULTS,
  ADVANCED_AI_LIMITS,
  type AdvancedAIBestConfig,
  type AdvancedAIGenerationEntry,
  type AdvancedAIRequest,
  type AdvancedAIResult,
} from "../types/advancedAi";

const HONEST_BOUNDS_NOTE =
  "Decision-support only. Scores measure group consistency, not legal scope or market opportunity.";

function formatScore(value: number | null | undefined, digits = 4): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function formatImprovement(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(4)}`;
}

function formatConfigValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return String(value);
  return String(value);
}

interface FormState {
  baseline_cluster_count: number;
  population_size: number;
  generations: number;
  mutation_rate: number;
  random_state: number;
}

const INITIAL_FORM: FormState = { ...ADVANCED_AI_DEFAULTS };

export function AdvancedAIPage() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);

  const optimizationMutation = useMutation({
    mutationFn: (request: AdvancedAIRequest) =>
      runAdvancedAIOptimization(request),
  });

  const isRunning = optimizationMutation.isPending;
  const result = optimizationMutation.data;
  const error = optimizationMutation.error;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (isRunning) return;
    optimizationMutation.mutate(form);
  };

  const resetForm = () => {
    setForm(INITIAL_FORM);
  };

  return (
    <section>
      <PageHeader
        eyebrow="Data & Methods"
        title="Method & Validation"
        description="How grouping is computed, optimized, and validated for the loaded corpus."
        actions={
          <>
            <Link className="link-button" to="/map">
              Open Map
            </Link>
            <Link className="link-button" to="/analytics">
              Open Trends &amp; Players
            </Link>
          </>
        }
        meta={
          <>
            <Badge variant="neutral">Grouping method</Badge>
            <Badge variant="accent">Optimization evidence</Badge>
            <Badge variant="neutral">Decision-support signals</Badge>
          </>
        }
      />

      {/* Part 1 — plain-language explainer for the curious. Kept short. */}
      <HowGroupingWorks />

      {/* Part 2 — the academic deliverable: what we measure, an honest
          statement of what is implemented, and the live evidence from a run. */}
      <MethodValidationIntro />

      {isRunning && (
        <div className="aai-runstate" role="status" aria-live="polite">
          <span className="aai-runstate__spinner" aria-hidden="true" />
          <div>
            <strong>Refreshing grouping quality evidence…</strong>
            <div style={{ fontSize: "0.85rem", marginTop: "0.15rem" }}>
              Evaluating {form.population_size} candidates across{" "}
              {form.generations} rounds.
            </div>
          </div>
        </div>
      )}

      {error && !isRunning && (
        <ErrorState
          title="Evidence refresh failed"
          message={
            error instanceof ApiError
              ? error.detail
              : error instanceof Error
              ? error.message
              : String(error)
          }
          hint="Check the backend and load a curated corpus."
        />
      )}

      {!result && !isRunning && !error && <BeforeRunPanel form={form} />}

      {result && !isRunning && <AdvancedAIResultPanel result={result} />}

      {/* Part 3 — raw GA controls + the run, demoted behind an expander so a
          visitor never lands on the knobs first. The run still hits the
          unchanged /api/advanced-ai endpoint. */}
      <AdvancedOptimizationPanel
        form={form}
        isRunning={isRunning}
        onChange={setForm}
        onSubmit={handleSubmit}
        onReset={resetForm}
        hasResult={Boolean(result)}
      />
    </section>
  );
}

interface ControlsProps {
  form: FormState;
  isRunning: boolean;
  hasResult: boolean;
  onChange: (next: FormState) => void;
  onSubmit: (event: React.FormEvent) => void;
  onReset: () => void;
}

function AdvancedAIControls({
  form,
  isRunning,
  hasResult,
  onChange,
  onSubmit,
  onReset,
}: ControlsProps) {
  const update =
    (key: keyof FormState) =>
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const raw = event.target.value;
      const next: FormState = {
        ...form,
        [key]: raw === "" ? 0 : Number(raw),
      };
      onChange(next);
    };

  return (
    <form className="card" onSubmit={onSubmit}>
      <header className="card__head">
        <div className="card__head-text">
          <h2 className="card__title">Run validation evidence</h2>
          <p className="card__description">
            Reviews grouping settings for the loaded corpus.
          </p>
        </div>
      </header>

      <div className="aai-controls__grid">
        <NumberField
          label="Baseline technology groups"
          hint="Comparison baseline."
          value={form.baseline_cluster_count}
          onChange={update("baseline_cluster_count")}
          limits={ADVANCED_AI_LIMITS.baseline_cluster_count}
          disabled={isRunning}
        />
        <NumberField
          label="Population size"
          hint="Candidates per round."
          value={form.population_size}
          onChange={update("population_size")}
          limits={ADVANCED_AI_LIMITS.population_size}
          disabled={isRunning}
        />
        <NumberField
          label="Optimization rounds"
          hint="Backend optimization rounds."
          value={form.generations}
          onChange={update("generations")}
          limits={ADVANCED_AI_LIMITS.generations}
          disabled={isRunning}
        />
        <NumberField
          label="Mutation rate"
          hint="Random-change probability."
          value={form.mutation_rate}
          onChange={update("mutation_rate")}
          limits={ADVANCED_AI_LIMITS.mutation_rate}
          disabled={isRunning}
        />
        <NumberField
          label="Random seed"
          hint="Repeatable runs."
          value={form.random_state}
          onChange={update("random_state")}
          limits={ADVANCED_AI_LIMITS.random_state}
          disabled={isRunning}
        />
      </div>

      <div className="aai-controls__actions">
        <button type="submit" className="button button--lg" disabled={isRunning}>
          {isRunning
            ? "Refreshing validation evidence…"
            : hasResult
            ? "Refresh validation evidence"
            : "Run validation evidence"}
        </button>
        <button
          type="button"
          className="button button--ghost"
          onClick={onReset}
          disabled={isRunning}
        >
          Reset to defaults
        </button>
      </div>
    </form>
  );
}

interface NumberFieldProps {
  label: string;
  hint: string;
  value: number;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  limits: { min: number; max: number; step: number };
  disabled?: boolean;
}

function NumberField({
  label,
  hint,
  value,
  onChange,
  limits,
  disabled,
}: NumberFieldProps) {
  return (
    <label className="filter-field aai-field">
      <span className="filter-field__label">{label}</span>
      <input
        type="number"
        value={Number.isFinite(value) ? value : ""}
        min={limits.min}
        max={limits.max}
        step={limits.step}
        onChange={onChange}
        disabled={disabled}
      />
      <span className="aai-field__hint">{hint}</span>
    </label>
  );
}

function BeforeRunPanel({ form }: { form: FormState }) {
  return (
    <SectionCard
      title="No validation run yet"
      description="Run validation evidence to compare baseline and optimized grouping."
    >
      <ul className="ga-preview-list">
        <li>
          <strong>Convergence chart</strong> — best and average fitness across
          all {form.generations} rounds, with the strongest round
          marked.
        </li>
        <li>
          <strong>Standard vs optimized comparison</strong> — baseline
          silhouette score next to the optimized score, plus the configuration
          the optimizer chose.
        </li>
        <li>
          <strong>Optimized technology groups</strong> — sizes and
          characteristic terms for the recommended clustering configuration.
        </li>
        <li>
          <strong>Per-round table</strong> — the full numeric history,
          tucked under <em>Developer details</em> for verification.
        </li>
      </ul>
    </SectionCard>
  );
}

// Part 1 — "Grouping method": a short, visual explainer for curious users.
// Three steps, not a manual. The detailed six-stage GA walkthrough lives in the
// Advanced expander for anyone who wants it.
const GROUPING_STEPS: Array<{ title: string; body: string }> = [
  {
    title: "Represent",
    body:
      "Titles, abstracts, and terms become comparable text features.",
  },
  {
    title: "Cluster",
    body:
      "Similar records form technology groups.",
  },
  {
    title: "Validate",
    body:
      "A genetic optimizer tests grouping settings.",
  },
];

function HowGroupingWorks() {
  return (
    <SectionCard
      title="Grouping method"
      description="Text-feature similarity, clustering, and validation evidence."
    >
      <ol className="ga-process" aria-label="Grouping method in three steps">
        {GROUPING_STEPS.map((entry, idx) => (
          <li key={entry.title} className="ga-process__item">
            <span className="ga-process__step">{idx + 1}</span>
            <span className="ga-process__title">{entry.title}</span>
            <span className="ga-process__body">{entry.body}</span>
          </li>
        ))}
      </ol>
    </SectionCard>
  );
}

// Part 2 — "Method & validation": the academic deliverable. What we measure,
// an honest statement of what is implemented, then the live run evidence.
function MethodValidationIntro() {
  const measures = [
    {
      label: "Clustering quality",
      title: "Silhouette score",
      body:
        "Unsupervised cluster-quality score from −1 to 1: close within groups, separated across groups. Values near 0 are expected in a narrow single-domain corpus where patent wording overlaps.",
    },
    {
      label: "Coherence",
      title: "Cluster coherence",
      body:
        "Whether groups hold together through terms and size distribution.",
    },
  ];

  return (
    <SectionCard
      title="Optimization evidence"
      description="Academic evidence and debug context for the loaded corpus."
    >
      <div className="method-evidence-grid">
        {measures.map((card) => (
          <article key={card.title} className="method-evidence-card">
            <div className="method-evidence-card__head">
              <Badge variant="neutral">{card.label}</Badge>
              <h3>{card.title}</h3>
            </div>
            <p>{card.body}</p>
          </article>
        ))}
      </div>

      <Callout variant="info" title="Optimizer scope in this build">
        <p>
          <strong>GA</strong> is implemented for grouping validation.{" "}
          <strong>PSO</strong> is not wired in this build.
        </p>
      </Callout>

      <p className="card__muted" style={{ marginTop: "0.6rem" }}>
        {HONEST_BOUNDS_NOTE}
      </p>
    </SectionCard>
  );
}

// Part 3 — raw GA controls + the detailed method walkthrough, demoted behind a
// native <details> expander so the knobs are never the first thing a visitor
// sees. The run itself is unchanged (same /api/advanced-ai integration).
function AdvancedOptimizationPanel(props: ControlsProps) {
  return (
    <div className="card">
      <details>
        <summary className="card__disclosure">
          Advanced experiment controls
        </summary>
        <div className="card__disclosure-body">
          <p className="card__muted" style={{ marginTop: 0 }}>
            Developer controls for refreshing validation evidence.
          </p>
          <AdvancedAIControls {...props} />
          <OptimizedGroupingProcessCard />
        </div>
      </details>
    </div>
  );
}

const PROCESS_STEPS: ProcessStep[] = [
  {
    step: 1,
    title: "Candidate configurations",
    body:
      "Each candidate is a full clustering setting.",
  },
  {
    step: 2,
    title: "Fitness evaluation",
    body:
      "Candidates are scored with the silhouette metric.",
  },
  {
    step: 3,
    title: "Selection",
    body:
      "Higher-fitness candidates continue.",
  },
  {
    step: 4,
    title: "Mutation & recombination",
    body:
      "Surviving candidates are combined and adjusted.",
  },
  {
    step: 5,
    title: "Optimization rounds",
    body:
      "Fitness is tracked across rounds.",
  },
  {
    step: 6,
    title: "Best configuration",
    body:
      "The strongest candidate is returned as evidence.",
  },
];

interface ProcessStep {
  step: number;
  title: string;
  body: string;
}

function OptimizedGroupingProcessCard() {
  return (
    <SectionCard
      title="How the grouping is improved"
      description="Backend GA stages for each evidence run."
    >
      <ol className="ga-process" aria-label="Optimized grouping stages">
        {PROCESS_STEPS.map((entry) => (
          <li key={entry.step} className="ga-process__item">
            <span className="ga-process__step">{entry.step}</span>
            <span className="ga-process__title">{entry.title}</span>
            <span className="ga-process__body">{entry.body}</span>
          </li>
        ))}
      </ol>
    </SectionCard>
  );
}

function AdvancedAIResultPanel({ result }: { result: AdvancedAIResult }) {
  const clusterEntries = Object.entries(result.optimized_cluster_sizes).filter(
    ([, value]) => value > 0,
  );
  const totalAssignments = clusterEntries.reduce(
    (sum, [, value]) => sum + value,
    0,
  );
  const termsEntries = Object.entries(
    result.optimized_top_terms_per_cluster,
  ).filter(([, terms]) => terms.length > 0);

  const improvement = result.improvement_over_baseline;
  let improvementHint: string | undefined;
  let improvementVariant: "success" | "warning" | "default" = "default";
  if (improvement !== null && improvement !== undefined) {
    if (improvement > 0) {
      improvementHint = "Optimized score is higher";
      improvementVariant = "success";
    } else if (improvement < 0) {
      improvementHint = "Optimized score is lower";
      improvementVariant = "warning";
    } else {
      improvementHint = "No change versus baseline";
    }
  }

  return (
    <>
      <Callout
        variant={result.runnable ? "success" : "warning"}
        title={
          result.runnable
            ? "Optimization evidence complete"
            : "Optimization evidence finished without a valid solution"
        }
      >
        <p>{result.status_message}</p>
      </Callout>

      <SectionCard
        title="Optimized grouping evidence"
        description="Summary metrics from the current evidence run."
      >
        <div className="metric-grid metric-grid--inside-card">
          <MetricCard
            label="Baseline grouping quality"
            value={formatScore(result.baseline_score)}
            hint="Silhouette score (−1 to 1) for the baseline grouping"
          />
          <MetricCard
            label="Optimized grouping quality"
            value={formatScore(result.best_score)}
            hint="Silhouette score (−1 to 1) for the strongest candidate"
            variant="primary"
          />
          <MetricCard
            label="Improvement"
            value={formatImprovement(improvement)}
            hint={improvementHint}
            variant={
              improvementVariant === "default" ? "default" : improvementVariant
            }
          />
          <MetricCard
            label="Best technology group count"
            value={
              result.best_config?.technology_group_count !== undefined
                ? String(result.best_config.technology_group_count)
                : "—"
            }
          />
        </div>
      </SectionCard>

      <ConvergenceSection history={result.generation_history} />

      <ComparisonSection result={result} />

      {result.best_config && (
        <BestConfigurationSection config={result.best_config} />
      )}

      {clusterEntries.length > 0 && (
        <SectionCard
          title="Optimized technology group sizes"
          description="Records per optimized technology group."
        >
          <ul className="breakdown-list">
            {clusterEntries.map(([key, value]) => {
              const pct =
                totalAssignments > 0
                  ? Math.round((value / totalAssignments) * 100)
                  : 0;
              return (
                <li key={key} className="breakdown-list__row">
                  <div className="breakdown-list__head">
                    <span className="breakdown-list__label">{key}</span>
                    <span className="breakdown-list__value">
                      {value} ({pct}%)
                    </span>
                  </div>
                  <div className="breakdown-list__bar" aria-hidden="true">
                    <div
                      className="breakdown-list__bar-fill breakdown-list__bar-fill--accent"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </SectionCard>
      )}

      {termsEntries.length > 0 && (
        <SectionCard
          title="Top terms per optimized group"
          description="Frequent terms for each optimized group."
        >
          <ul className="tech-group-list">
            {termsEntries.map(([groupLabel, terms]) => (
              <li key={groupLabel} className="tech-group-list__item">
                <div className="tech-group-list__header">
                  <span className="tech-group-list__name">{groupLabel}</span>
                  <span className="tech-group-list__count">
                    {result.optimized_cluster_sizes[groupLabel] ?? 0} patents
                  </span>
                </div>
                <div className="chip-row">
                  {terms.slice(0, 10).map((term) => (
                    <span key={term} className="chip chip--keyword">
                      {term}
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}

      <DatasetWarningCallout warnings={result.warnings} />

      <TechnicalDetailsCard result={result} />
    </>
  );
}

function ConvergenceSection({
  history,
}: {
  history: AdvancedAIGenerationEntry[];
}) {
  if (history.length === 0) {
    return (
      <SectionCard
        title="Convergence over generations"
        description="Best and average fitness by round."
      >
        <p className="card__muted">
          The optimizer did not return any round history for this run.
          This can happen when the corpus has too few records for a full
          search, or when the run was halted early. The numeric scores above
          still reflect the best configuration found.
        </p>
      </SectionCard>
    );
  }
  return (
    <SectionCard
      title="Convergence over generations"
      description="Best and average fitness by round."
    >
      <ConvergenceChart history={history} />
    </SectionCard>
  );
}

interface ChartPoint {
  generation: number;
  bestScore: number | null;
  averageScore: number | null;
}

function ConvergenceChart({
  history,
}: {
  history: AdvancedAIGenerationEntry[];
}) {
  const [hovered, setHovered] = useState<number | null>(null);

  const points = useMemo<ChartPoint[]>(
    () =>
      history.map((h) => ({
        generation: h.generation,
        bestScore:
          typeof h.best_score === "number" && !Number.isNaN(h.best_score)
            ? h.best_score
            : null,
        averageScore:
          typeof h.average_score === "number" &&
          !Number.isNaN(h.average_score)
            ? h.average_score
            : null,
      })),
    [history],
  );

  const hasAverage = points.some((p) => p.averageScore !== null);
  const bestValues = points
    .map((p) => p.bestScore)
    .filter((v): v is number => v !== null);
  if (bestValues.length === 0) {
    return (
      <p className="card__muted">
        No fitness scores were reported for the recorded rounds.
      </p>
    );
  }

  const generations = points.map((p) => p.generation);
  const xMin = Math.min(...generations);
  const xMax = Math.max(...generations);

  const scoreValues = points.flatMap((p) =>
    [p.bestScore, p.averageScore].filter(
      (v): v is number => v !== null && !Number.isNaN(v),
    ),
  );
  let yMinRaw = Math.min(...scoreValues);
  let yMaxRaw = Math.max(...scoreValues);
  if (yMinRaw === yMaxRaw) {
    yMinRaw -= 0.05;
    yMaxRaw += 0.05;
  }
  const yPadding = (yMaxRaw - yMinRaw) * 0.18;
  const yMin = yMinRaw - yPadding;
  const yMax = yMaxRaw + yPadding;

  const width = 760;
  const height = 300;
  const padding = { top: 18, right: 28, bottom: 40, left: 64 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const xScale = (g: number) =>
    padding.left + ((g - xMin) / Math.max(1, xMax - xMin)) * innerW;
  const yScale = (s: number) =>
    padding.top + (1 - (s - yMin) / Math.max(1e-9, yMax - yMin)) * innerH;

  const yTicks = computeNiceTicks(yMin, yMax, 5);
  const xTicks = generations;

  // Find the strongest round (highest best_score). If multiple share
  // the maximum, pick the earliest — that's when convergence first reached it.
  let bestIdx = 0;
  let bestVal = -Infinity;
  for (let i = 0; i < points.length; i += 1) {
    const value = points[i].bestScore;
    if (value !== null && value > bestVal) {
      bestVal = value;
      bestIdx = i;
    }
  }
  const bestPoint = points[bestIdx];

  const bestSegments = buildSegments(points.map((p) => p.bestScore));
  const avgSegments = hasAverage
    ? buildSegments(points.map((p) => p.averageScore))
    : [];

  const bestPathD = segmentsToPath(bestSegments, points, xScale, yScale, "best");
  const bestAreaD = segmentsToArea(
    bestSegments,
    points,
    xScale,
    yScale,
    padding.top + innerH,
    "best",
  );
  const avgPathD = hasAverage
    ? segmentsToPath(avgSegments, points, xScale, yScale, "avg")
    : "";

  // Hover area: full chart width split into vertical bands per round.
  const bandWidth = innerW / Math.max(1, points.length);

  const summaryId = "ga-convergence-summary";

  return (
    <div className="ga-convergence">
      <div className="ga-convergence__legend" role="presentation">
        <span className="ga-convergence__legend-item ga-convergence__legend-item--best">
          <span className="ga-convergence__swatch" aria-hidden="true" />
          Best fitness per round
        </span>
        {hasAverage && (
          <span className="ga-convergence__legend-item ga-convergence__legend-item--avg">
            <span className="ga-convergence__swatch ga-convergence__swatch--avg" aria-hidden="true" />
            Average fitness per round
          </span>
        )}
        <span className="ga-convergence__legend-item ga-convergence__legend-item--best-marker">
          <span className="ga-convergence__swatch ga-convergence__swatch--marker" aria-hidden="true" />
          Strongest round
        </span>
      </div>

      <div className="ga-convergence__chart-wrap">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-labelledby={summaryId}
          className="ga-convergence__chart"
        >
          <title id={summaryId}>
            Convergence chart: best fitness rose from{" "}
            {formatScore(points[0].bestScore)} at round {points[0].generation}{" "}
            to {formatScore(bestPoint.bestScore)} at round{" "}
            {bestPoint.generation} across {points.length} round
            {points.length === 1 ? "" : "s"}.
          </title>

          {/* Plot area background */}
          <rect
            x={padding.left}
            y={padding.top}
            width={innerW}
            height={innerH}
            fill="var(--color-surface-2)"
            stroke="var(--color-border)"
          />

          {/* Y gridlines + labels */}
          {yTicks.map((t) => (
            <g key={`y-${t}`}>
              <line
                x1={padding.left}
                x2={padding.left + innerW}
                y1={yScale(t)}
                y2={yScale(t)}
                stroke="var(--color-border)"
                strokeDasharray="3,3"
                strokeWidth={1}
                opacity={0.6}
              />
              <text
                x={padding.left - 10}
                y={yScale(t) + 4}
                textAnchor="end"
                fontSize="11"
                fill="var(--color-text-muted)"
                fontFamily="var(--font-mono)"
              >
                {t.toFixed(3)}
              </text>
            </g>
          ))}

          {/* X-axis labels */}
          {xTicks.map((g) => (
            <text
              key={`x-${g}`}
              x={xScale(g)}
              y={padding.top + innerH + 18}
              textAnchor="middle"
              fontSize="11"
              fill="var(--color-text-muted)"
              fontFamily="var(--font-mono)"
            >
              {g}
            </text>
          ))}
          <text
            x={padding.left + innerW / 2}
            y={height - 6}
            textAnchor="middle"
            fontSize="11"
            fill="var(--color-text-muted)"
          >
            Round
          </text>
          <text
            x={14}
            y={padding.top + innerH / 2}
            textAnchor="middle"
            fontSize="11"
            fill="var(--color-text-muted)"
            transform={`rotate(-90 14 ${padding.top + innerH / 2})`}
          >
            Fitness (silhouette)
          </text>

          {/* Best-score filled area */}
          {bestAreaD && (
            <path
              d={bestAreaD}
              fill="url(#ga-best-gradient)"
              opacity={0.6}
            />
          )}

          <defs>
            <linearGradient
              id="ga-best-gradient"
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Average score line */}
          {hasAverage && avgPathD && (
            <path
              d={avgPathD}
              fill="none"
              stroke="var(--color-text-muted)"
              strokeWidth={1.6}
              strokeDasharray="5,4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Best score line */}
          {bestPathD && (
            <path
              d={bestPathD}
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth={2.4}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Round point markers (best score) */}
          {points.map(
            (p, idx) =>
              p.bestScore !== null && (
                <circle
                  key={`best-pt-${p.generation}`}
                  cx={xScale(p.generation)}
                  cy={yScale(p.bestScore)}
                  r={hovered === idx ? 5.5 : 3.5}
                  fill="var(--color-primary)"
                  stroke="#ffffff"
                  strokeWidth={1.5}
                />
              ),
          )}

          {/* Strongest round marker */}
          {bestPoint.bestScore !== null && (
            <g aria-hidden="true">
              <line
                x1={xScale(bestPoint.generation)}
                x2={xScale(bestPoint.generation)}
                y1={padding.top}
                y2={padding.top + innerH}
                stroke="var(--color-accent)"
                strokeWidth={1.2}
                strokeDasharray="4,4"
                opacity={0.55}
              />
              <circle
                cx={xScale(bestPoint.generation)}
                cy={yScale(bestPoint.bestScore)}
                r={8}
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth={2}
              />
            </g>
          )}

          {/* Hover bands */}
          {points.map((p, idx) => {
            const bandX = xScale(p.generation) - bandWidth / 2;
            return (
              <rect
                key={`band-${p.generation}`}
                x={Math.max(padding.left, bandX)}
                y={padding.top}
                width={Math.min(
                  bandWidth,
                  padding.left + innerW - Math.max(padding.left, bandX),
                )}
                height={innerH}
                fill="transparent"
                onMouseEnter={() => setHovered(idx)}
                onMouseLeave={() =>
                  setHovered((cur) => (cur === idx ? null : cur))
                }
                onFocus={() => setHovered(idx)}
                onBlur={() =>
                  setHovered((cur) => (cur === idx ? null : cur))
                }
                tabIndex={0}
                role="img"
                aria-label={`Round ${p.generation}: best ${formatScore(
                  p.bestScore,
                )}${
                  p.averageScore !== null
                    ? `, average ${formatScore(p.averageScore)}`
                    : ""
                }`}
                style={{ cursor: "crosshair", outline: "none" }}
              />
            );
          })}

          {/* Hover tooltip */}
          {hovered !== null && points[hovered] && (
            <ConvergenceTooltip
              point={points[hovered]}
              x={xScale(points[hovered].generation)}
              chartWidth={width}
              padding={padding}
              isBest={hovered === bestIdx}
            />
          )}
        </svg>
      </div>

      <p className="ga-convergence__caption">
        {hovered !== null && points[hovered] ? (
          <>
            Hovering round <strong>{points[hovered].generation}</strong> —
            best <strong>{formatScore(points[hovered].bestScore)}</strong>
            {points[hovered].averageScore !== null && (
              <>
                , average{" "}
                <strong>{formatScore(points[hovered].averageScore)}</strong>
              </>
            )}
            .
          </>
        ) : (
          <>
            Strongest round:{" "}
            <strong>round {bestPoint.generation}</strong> with fitness{" "}
            <strong>{formatScore(bestPoint.bestScore)}</strong>. The optimizer
            found the strongest clustering configuration according to the
            selected fitness metric.
          </>
        )}
      </p>
    </div>
  );
}

function ConvergenceTooltip({
  point,
  x,
  chartWidth,
  padding,
  isBest,
}: {
  point: ChartPoint;
  x: number;
  chartWidth: number;
  padding: { top: number; right: number; bottom: number; left: number };
  isBest: boolean;
}) {
  const tooltipWidth = 160;
  const tooltipHeight = point.averageScore !== null ? 70 : 56;
  const tooltipX = Math.min(
    chartWidth - padding.right - tooltipWidth,
    Math.max(padding.left, x - tooltipWidth / 2),
  );
  const tooltipY = padding.top + 6;
  return (
    <g pointerEvents="none">
      <rect
        x={tooltipX}
        y={tooltipY}
        width={tooltipWidth}
        height={tooltipHeight}
        rx={8}
        ry={8}
        fill="rgba(15, 23, 42, 0.94)"
        stroke="rgba(255, 255, 255, 0.08)"
      />
      <text
        x={tooltipX + 12}
        y={tooltipY + 18}
        fontSize="11"
        fontFamily="var(--font-mono)"
        fill="rgba(255,255,255,0.7)"
      >
        Round {point.generation}
        {isBest ? " · strongest" : ""}
      </text>
      <text
        x={tooltipX + 12}
        y={tooltipY + 36}
        fontSize="12"
        fill="#ffffff"
        fontFamily="var(--font-mono)"
      >
        Best: {formatScore(point.bestScore)}
      </text>
      {point.averageScore !== null && (
        <text
          x={tooltipX + 12}
          y={tooltipY + 54}
          fontSize="12"
          fill="rgba(255,255,255,0.75)"
          fontFamily="var(--font-mono)"
        >
          Avg: {formatScore(point.averageScore)}
        </text>
      )}
    </g>
  );
}

type Segment = number[]; // indices of contiguous non-null points

function buildSegments(values: (number | null)[]): Segment[] {
  const segs: Segment[] = [];
  let current: Segment = [];
  for (let i = 0; i < values.length; i += 1) {
    if (values[i] === null) {
      if (current.length > 0) segs.push(current);
      current = [];
    } else {
      current.push(i);
    }
  }
  if (current.length > 0) segs.push(current);
  return segs;
}

function segmentsToPath(
  segments: Segment[],
  points: ChartPoint[],
  xScale: (g: number) => number,
  yScale: (s: number) => number,
  series: "best" | "avg",
): string {
  const parts: string[] = [];
  for (const seg of segments) {
    seg.forEach((idx, i) => {
      const p = points[idx];
      const value = series === "best" ? p.bestScore : p.averageScore;
      if (value === null) return;
      const cmd = i === 0 ? "M" : "L";
      parts.push(`${cmd} ${xScale(p.generation)} ${yScale(value)}`);
    });
  }
  return parts.join(" ");
}

function segmentsToArea(
  segments: Segment[],
  points: ChartPoint[],
  xScale: (g: number) => number,
  yScale: (s: number) => number,
  baseY: number,
  series: "best" | "avg",
): string {
  const parts: string[] = [];
  for (const seg of segments) {
    if (seg.length === 0) continue;
    seg.forEach((idx, i) => {
      const p = points[idx];
      const value = series === "best" ? p.bestScore : p.averageScore;
      if (value === null) return;
      const cmd = i === 0 ? "M" : "L";
      parts.push(`${cmd} ${xScale(p.generation)} ${yScale(value)}`);
    });
    const lastIdx = seg[seg.length - 1];
    const firstIdx = seg[0];
    parts.push(`L ${xScale(points[lastIdx].generation)} ${baseY}`);
    parts.push(`L ${xScale(points[firstIdx].generation)} ${baseY} Z`);
  }
  return parts.join(" ");
}

function computeNiceTicks(min: number, max: number, target: number): number[] {
  if (max <= min) return [min];
  const range = max - min;
  const rough = range / target;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rough)));
  const candidates = [1, 2, 2.5, 5, 10].map((c) => c * magnitude);
  let step = candidates[0];
  for (const c of candidates) {
    if (c >= rough) {
      step = c;
      break;
    }
  }
  const start = Math.ceil(min / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= max + step / 2; v += step) {
    ticks.push(Number(v.toFixed(6)));
  }
  return ticks;
}

function ComparisonSection({ result }: { result: AdvancedAIResult }) {
  const standard = describeStandard(result);
  const optimized = describeOptimized(result);
  const improvement = result.improvement_over_baseline;
  let improvementBadge: "neutral" | "success" | "warning" = "neutral";
  if (improvement !== null && improvement !== undefined) {
    if (improvement > 0) improvementBadge = "success";
    else if (improvement < 0) improvementBadge = "warning";
  }
  return (
    <SectionCard
      title="Standard vs optimized grouping"
      description="Strongest candidate compared with the baseline."
    >
      <div className="ga-comparison">
        <div className="ga-comparison__column">
          <div className="ga-comparison__column-head">
            <Badge variant="neutral">Standard</Badge>
            <span className="ga-comparison__column-title">
              Baseline grouping
            </span>
          </div>
          <ComparisonRows rows={standard} />
        </div>
        <div className="ga-comparison__arrow" aria-hidden="true">
          →
        </div>
        <div className="ga-comparison__column ga-comparison__column--optimized">
          <div className="ga-comparison__column-head">
            <Badge variant="primary">Optimized</Badge>
            <span className="ga-comparison__column-title">
              Strongest configuration
            </span>
          </div>
          <ComparisonRows rows={optimized} />
          {improvement !== null && improvement !== undefined && (
            <div className={`ga-comparison__delta ga-comparison__delta--${improvementBadge}`}>
              <span className="ga-comparison__delta-label">
                Improvement vs baseline
              </span>
              <span className="ga-comparison__delta-value">
                {formatImprovement(improvement)}
              </span>
            </div>
          )}
        </div>
      </div>
      <p className="card__muted ga-comparison__note">
        The optimizer found the strongest clustering configuration according to
        the selected fitness metric. A higher score does not mean the grouping
        is proven correct; it means it is more internally consistent and
        better separated on the current corpus.
      </p>
    </SectionCard>
  );
}

function BestConfigurationSection({ config }: { config: AdvancedAIBestConfig }) {
  return (
    <SectionCard
      title="Best configuration"
      description="Grouping settings returned by the evidence run."
    >
      <BestConfigInline config={config} />
    </SectionCard>
  );
}

interface ComparisonRow {
  label: string;
  value: string;
  hint?: string;
}

function describeStandard(result: AdvancedAIResult): ComparisonRow[] {
  const rows: ComparisonRow[] = [];
  rows.push({
    label: "Silhouette score",
    value: formatScore(result.baseline_score),
    hint: "Fitness metric on the baseline grouping",
  });
  const baselineCount = result.settings["baseline_cluster_count"];
  if (typeof baselineCount === "number") {
    rows.push({
      label: "Technology group count",
      value: String(baselineCount),
      hint: "Clusters used as the comparison baseline",
    });
  }
  return rows;
}

function describeOptimized(result: AdvancedAIResult): ComparisonRow[] {
  const rows: ComparisonRow[] = [];
  rows.push({
    label: "Silhouette score",
    value: formatScore(result.best_score),
    hint: "Fitness metric on the strongest candidate",
  });
  const cfg = result.best_config;
  if (cfg?.technology_group_count !== undefined) {
    rows.push({
      label: "Technology group count",
      value: formatConfigValue(cfg.technology_group_count),
      hint: "Clusters chosen by the optimizer",
    });
  }
  if (cfg?.keyword_evidence_feature_limit !== undefined) {
    rows.push({
      label: "Keyword evidence feature limit",
      value: formatConfigValue(cfg.keyword_evidence_feature_limit),
      hint: 'TF-IDF max-features setting ("None" means no cap)',
    });
  }
  if (cfg?.keyword_phrase_upper_bound !== undefined) {
    rows.push({
      label: "Keyword phrase upper bound",
      value: formatConfigValue(cfg.keyword_phrase_upper_bound),
      hint: "Max n-gram length used as keyword evidence",
    });
  }
  return rows;
}

function ComparisonRows({ rows }: { rows: ComparisonRow[] }) {
  if (rows.length === 0) {
    return (
      <p className="card__muted" style={{ fontSize: "0.84rem" }}>
        No comparable fields were returned.
      </p>
    );
  }
  return (
    <dl className="ga-comparison__rows">
      {rows.map((row) => (
        <div key={row.label} className="ga-comparison__row">
          <dt>{row.label}</dt>
          <dd>{row.value}</dd>
          {row.hint && <span className="ga-comparison__hint">{row.hint}</span>}
        </div>
      ))}
    </dl>
  );
}

function GenerationHistoryTable({
  history,
}: {
  history: AdvancedAIGenerationEntry[];
}) {
  if (history.length === 0) {
    return (
      <p className="card__muted" style={{ fontSize: "0.84rem" }}>
        No per-round history was returned for this run.
      </p>
    );
  }
  return (
    <div className="ga-generation-table">
      <table className="relationships-table">
        <thead>
          <tr>
            <th scope="col">Round</th>
            <th scope="col">Best score</th>
            <th scope="col">Average score</th>
          </tr>
        </thead>
        <tbody>
          {history.map((entry) => (
            <tr key={entry.generation}>
              <td>{entry.generation}</td>
              <td style={{ fontVariantNumeric: "tabular-nums" }}>
                {formatScore(entry.best_score)}
              </td>
              <td style={{ fontVariantNumeric: "tabular-nums" }}>
                {formatScore(entry.average_score)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TechnicalDetailsCard({ result }: { result: AdvancedAIResult }) {
  const settingsEntries = Object.entries(result.settings);
  if (settingsEntries.length === 0 && result.generation_history.length === 0) {
    return null;
  }
  return (
    <div className="card">
      <details>
        <summary className="card__disclosure">Developer details</summary>
        <div className="card__disclosure-body">
          {result.generation_history.length > 0 && (
            <>
              <h3 className="ga-tech__heading">Per-round history</h3>
              <GenerationHistoryTable history={result.generation_history} />
            </>
          )}
          {settingsEntries.length > 0 && (
            <>
              <h3 className="ga-tech__heading">Run settings</h3>
              <table className="metadata-table">
                <tbody>
                  {settingsEntries.map(([key, value]) => (
                    <tr key={key}>
                      <th scope="row">{key}</th>
                      <td>{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </details>
    </div>
  );
}

function BestConfigInline({ config }: { config: AdvancedAIBestConfig }) {
  const rows: Array<{ label: string; value: string }> = [];
  if (config.technology_group_count !== undefined) {
    rows.push({
      label: "Technology group count",
      value: formatConfigValue(config.technology_group_count),
    });
  }
  if (config.keyword_evidence_feature_limit !== undefined) {
    rows.push({
      label: "Keyword evidence feature limit",
      value: formatConfigValue(config.keyword_evidence_feature_limit),
    });
  }
  if (config.keyword_phrase_upper_bound !== undefined) {
    rows.push({
      label: "Keyword phrase upper bound",
      value: formatConfigValue(config.keyword_phrase_upper_bound),
    });
  }
  if (rows.length === 0) {
    return (
      <p className="card__muted" style={{ fontSize: "0.84rem" }}>
        No configuration fields were returned.
      </p>
    );
  }
  return (
    <table className="metadata-table">
      <tbody>
        {rows.map((row) => (
          <tr key={row.label}>
            <th scope="row">{row.label}</th>
            <td>{row.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
