import type { ProfileApplicationArea, RelatedPatent } from "../../types/patents";
import {
  ApplicationSignalBadge,
  getApplicationSignalInfo,
} from "./ApplicationSignalBadge";

const MAX_VISIBLE_TERMS = 8;
const MAX_VISIBLE_RELATED = 3;
const MAX_VISIBLE_GROUPS = 2;

export interface AreaEvidenceSummary {
  relatedSupportCount: number;
  relatedSupportSamples: RelatedPatent[];
  sharedTechnologyGroups: string[];
  sameGroupSupport: number;
}

function normalizeAreaName(value: string): string {
  return value.trim().toLowerCase();
}

export function summarizeAreaEvidence(
  area: ProfileApplicationArea,
  related: RelatedPatent[],
): AreaEvidenceSummary {
  const target = normalizeAreaName(area.area_name);
  const supporting: RelatedPatent[] = [];
  const groupCounts = new Map<string, number>();
  let sameGroupSupport = 0;
  for (const rel of related) {
    const matches = rel.candidate_application_areas.some(
      (candidate) => normalizeAreaName(candidate) === target,
    );
    if (!matches) continue;
    supporting.push(rel);
    if (rel.same_technology_group) sameGroupSupport += 1;
    const group = rel.target_technology_group || rel.source_technology_group;
    if (group) {
      groupCounts.set(group, (groupCounts.get(group) ?? 0) + 1);
    }
  }
  const sharedTechnologyGroups = Array.from(groupCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([name]) => name);
  return {
    relatedSupportCount: supporting.length,
    relatedSupportSamples: supporting.slice(0, MAX_VISIBLE_RELATED),
    sharedTechnologyGroups,
    sameGroupSupport,
  };
}

function describeScore(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return "—";
  return score.toFixed(2);
}

function buildHeadlineSentence(
  area: ProfileApplicationArea,
  evidence: AreaEvidenceSummary,
): string {
  const info = getApplicationSignalInfo(area.evidence_level);
  const hasTerms = area.matched_terms.length > 0;
  const hasRelated = evidence.relatedSupportCount > 0;

  if (hasTerms && hasRelated) {
    return "Suggested from matched technical terms and relationship-neighborhood context.";
  }
  if (hasTerms) {
    return "Suggested from matched technical signals in the patent text.";
  }
  if (hasRelated) {
    return "Suggested from candidate areas shared with nearby related patents.";
  }
  if (info.tier === "early") {
    return "Partial evidence only — useful as a reading aid for deeper review.";
  }
  return "Candidate reading aid based on available technical signals.";
}

interface CandidateApplicationAreaCardProps {
  area: ProfileApplicationArea;
  related: RelatedPatent[];
}

export function CandidateApplicationAreaCard({
  area,
  related,
}: CandidateApplicationAreaCardProps) {
  const evidence = summarizeAreaEvidence(area, related);
  const info = getApplicationSignalInfo(area.evidence_level);
  const headline = buildHeadlineSentence(area, evidence);
  const visibleTerms = area.matched_terms.slice(0, MAX_VISIBLE_TERMS);
  const hiddenTerms = area.matched_terms.length - visibleTerms.length;
  const visibleGroups = evidence.sharedTechnologyGroups.slice(
    0,
    MAX_VISIBLE_GROUPS,
  );
  const hiddenGroups = evidence.sharedTechnologyGroups.length - visibleGroups.length;
  const hiddenRelated =
    evidence.relatedSupportCount - evidence.relatedSupportSamples.length;

  return (
    <li
      className={`candidate-area-card candidate-area-card--${info.tier}`}
      aria-label={`Candidate application area: ${area.area_name}. ${info.label}.`}
    >
      <div className="candidate-area-card__head">
        <div className="candidate-area-card__title-row">
          <h3 className="candidate-area-card__title">{area.area_name}</h3>
          <ApplicationSignalBadge evidenceLevel={area.evidence_level} />
        </div>
        <p className="candidate-area-card__headline">{headline}</p>
      </div>

      <dl className="candidate-area-card__signal-row">
        <div className="candidate-area-card__signal">
          <dt>Signal score</dt>
          <dd>{describeScore(area.score)}</dd>
        </div>
        <div className="candidate-area-card__signal">
          <dt>Matched terms</dt>
          <dd>{area.evidence_count || area.matched_terms.length}</dd>
        </div>
        <div className="candidate-area-card__signal">
          <dt>Related-record support</dt>
          <dd>{evidence.relatedSupportCount}</dd>
        </div>
      </dl>

      {visibleTerms.length > 0 && (
        <div className="candidate-area-card__section">
          <span className="candidate-area-card__section-label">
            Matched technical signals
          </span>
          <div className="chip-row">
            {visibleTerms.map((term) => (
              <span key={term} className="chip chip--keyword">
                {term}
              </span>
            ))}
            {hiddenTerms > 0 && (
              <span className="chip chip--muted">+{hiddenTerms} more</span>
            )}
          </div>
        </div>
      )}

      {evidence.relatedSupportCount > 0 && (
        <div className="candidate-area-card__section">
          <span className="candidate-area-card__section-label">
            Related-record support
          </span>
          <ul className="candidate-area-card__related">
            {evidence.relatedSupportSamples.map((rel) => (
              <li key={rel.analysis_id} className="candidate-area-card__related-item">
                <span className="candidate-area-card__related-title">
                  {rel.title || rel.patent_id}
                </span>
                <span className="candidate-area-card__related-meta">
                  {rel.patent_id}
                  {rel.same_technology_group ? " · same technology group" : ""}
                </span>
              </li>
            ))}
            {hiddenRelated > 0 && (
              <li className="candidate-area-card__related-more">
                +{hiddenRelated} more related record
                {hiddenRelated === 1 ? "" : "s"} in the corpus also list this
                area.
              </li>
            )}
          </ul>
        </div>
      )}

      {visibleGroups.length > 0 && (
        <div className="candidate-area-card__section">
          <span className="candidate-area-card__section-label">
            Technology-group fit
          </span>
          <div className="chip-row">
            {visibleGroups.map((group) => (
              <span key={group} className="chip chip--area">
                {group}
              </span>
            ))}
            {hiddenGroups > 0 && (
              <span className="chip chip--muted">+{hiddenGroups} more</span>
            )}
          </div>
          {evidence.sameGroupSupport > 0 && (
            <p className="candidate-area-card__group-hint">
              {evidence.sameGroupSupport} related record
              {evidence.sameGroupSupport === 1 ? "" : "s"} in this area sit in
              the same technology group as this patent.
            </p>
          )}
        </div>
      )}

      {area.explanation && (
        <p className="candidate-area-card__explanation">{area.explanation}</p>
      )}

      <p className="candidate-area-card__footnote">
        Candidate area for review, not a guaranteed market classification.
      </p>
    </li>
  );
}
