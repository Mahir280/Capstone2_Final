import type { ReactNode } from "react";

import { Callout } from "../common/Callout";
import { SectionCard } from "../common/SectionCard";
import { OpportunitySignalCard } from "./OpportunitySignalCard";
import type { OpportunitySignal } from "./types";

export type OpportunityScope =
  | "full-corpus"
  | "current-visible"
  | "focused-neighborhood";

const SCOPE_LABEL: Record<OpportunityScope, string> = {
  "full-corpus": "Full loaded corpus.",
  "current-visible": "Visible map only.",
  "focused-neighborhood":
    "Focused neighborhood only.",
};

interface OpportunitySignalsPanelProps {
  signals: OpportunitySignal[];
  scope: OpportunityScope;
  title?: string;
  intro?: ReactNode;
  emptyMessage?: string;
}

export function OpportunitySignalsPanel({
  signals,
  scope,
  title = "Opportunity signals",
  intro,
  emptyMessage,
}: OpportunitySignalsPanelProps) {
  const scopeLabel = SCOPE_LABEL[scope];

  const description = (
    <>
      {intro ??
        "Low-density, lighter-group, assignee, and cross-over signals."}
      <span className="opportunity-panel__scope-inline"> {scopeLabel}</span>
    </>
  );

  return (
    <SectionCard title={title} description={description}>
      <div
        className="opportunity-panel__legend"
        aria-label="How to read opportunity signals"
      >
        <div className="opportunity-panel__legend-item">
          <span className="opportunity-panel__legend-dot opportunity-panel__legend-dot--strong" />
          <div>
            <strong>Strong review signal</strong>
            <span>Multiple indicators agree.</span>
          </div>
        </div>
        <div className="opportunity-panel__legend-item">
          <span className="opportunity-panel__legend-dot opportunity-panel__legend-dot--moderate" />
          <div>
            <strong>Moderate review signal</strong>
            <span>Some indicators agree.</span>
          </div>
        </div>
        <div className="opportunity-panel__legend-item">
          <span className="opportunity-panel__legend-dot opportunity-panel__legend-dot--early" />
          <div>
            <strong>Early review signal</strong>
            <span>Limited corpus evidence.</span>
          </div>
        </div>
      </div>

      <Callout variant="info" role="note">
        <p style={{ margin: 0 }}>
          Exploratory signals from the current corpus only — not legal advice
          or a market guarantee. Low density does not guarantee opportunity;
          expert review is required before strategic use.
        </p>
      </Callout>

      {signals.length === 0 ? (
        <p className="card__muted">
          {emptyMessage ??
            "No signals for the current view."}
        </p>
      ) : (
        <ul className="opportunity-panel__grid">
          {signals.map((signal) => (
            <OpportunitySignalCard key={signal.id} signal={signal} />
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
