import { useMemo } from "react";
import { Link } from "react-router-dom";

import { encodeAnalysisId } from "../../api/patents";
import type {
  ProfileApplicationArea,
  RelatedPatent,
} from "../../types/patents";
import { Badge } from "../common/Badge";
import { RelationshipStrengthMeter } from "./RelationshipStrengthMeter";
import { SharedEvidenceChips } from "./SharedEvidenceChips";

function describeNumber(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

interface ReasonItem {
  key: string;
  icon: string;
  title: string;
  body: string;
}

interface RelationshipReasons {
  headline: string;
  items: ReasonItem[];
}

export function buildRelationshipReasons(
  rel: RelatedPatent,
  profileAreas: ProfileApplicationArea[],
  profileAuthority: string | null,
): RelationshipReasons {
  const items: ReasonItem[] = [];
  const score = rel.similarity_score;
  const headlineParts: string[] = [];

  let similarityLabel = "moderate";
  if (score >= 0.65) similarityLabel = "strong";
  else if (score < 0.35) similarityLabel = "early";
  items.push({
    key: "similarity",
    icon: "≈",
    title: "Text-vector similarity",
    body:
      `${similarityLabel} textual similarity (score ${describeNumber(
        score,
      )}); strength label: "${rel.relationship_strength}".`,
  });
  headlineParts.push(`${rel.relationship_strength} similarity`);

  if (rel.same_technology_group) {
    items.push({
      key: "same-group",
      icon: "◎",
      title: "Same technology group",
      body: rel.target_technology_group
        ? `Both patents appear in "${rel.target_technology_group}".`
        : "Both patents appear in the same technology group.",
    });
    headlineParts.push("same technology group");
  } else if (
    rel.source_technology_group &&
    rel.target_technology_group &&
    rel.source_technology_group !== rel.target_technology_group
  ) {
    items.push({
      key: "cross-group",
      icon: "↔",
      title: "Cross-group relationship",
      body: `Bridges "${rel.source_technology_group}" and "${rel.target_technology_group}".`,
    });
    headlineParts.push("cross technology group");
  }

  if (rel.shared_keywords.length > 0) {
    items.push({
      key: "shared-keywords",
      icon: "#",
      title: "Shared technical signals",
      body: `${rel.shared_keywords.length} shared keyword${
        rel.shared_keywords.length === 1 ? "" : "s"
      }: ${rel.shared_keywords
        .slice(0, 6)
        .join(", ")}${rel.shared_keywords.length > 6 ? ", …" : ""}.`,
    });
  }

  if (rel.overlap_signal) {
    items.push({
      key: "overlap",
      icon: "⊙",
      title: "Overlap signal",
      body: `Overlap signal is "${rel.overlap_signal}" (score ${describeNumber(
        rel.overlap_score,
      )}). Review aid only.`,
    });
  }

  const profileAreaNames = new Set(
    profileAreas.map((a) => a.area_name.toLowerCase()),
  );
  const shared = rel.candidate_application_areas.filter((area) =>
    profileAreaNames.has(area.toLowerCase()),
  );
  if (shared.length > 0) {
    items.push({
      key: "shared-areas",
      icon: "★",
      title: "Shared candidate application areas",
      body: `Both patents have keyword-based evidence for: ${shared
        .slice(0, 5)
        .join(", ")}${shared.length > 5 ? ", …" : ""}.`,
    });
  }

  const relAuthority = rel.source_authority || rel.source;
  if (
    profileAuthority &&
    relAuthority &&
    relAuthority.toLowerCase() !== profileAuthority.toLowerCase()
  ) {
    items.push({
      key: "cross-authority",
      icon: "✦",
      title: "Cross-authority link",
      body: `Source-authority bridge: ${profileAuthority} ↔ ${relAuthority}. Cross-authority links often add useful relationship-neighborhood context.`,
    });
    headlineParts.push(`cross-authority (${relAuthority})`);
  }

  if (items.length === 0) {
    items.push({
      key: "fallback",
      icon: "•",
      title: "Similarity-based relationship",
      body: "Based on similarity signals from available patent text.",
    });
  }

  const headline =
    headlineParts.length > 0
      ? headlineParts.slice(0, 3).join(" · ")
      : "similarity signal";
  return { headline, items };
}

interface RelatedPatentDossierCardProps {
  rel: RelatedPatent;
  profileAreas: ProfileApplicationArea[];
  profileAuthority: string | null;
  onCompare: (analysisId: string) => void;
  isCompared: boolean;
}

export function RelatedPatentDossierCard({
  rel,
  profileAreas,
  profileAuthority,
  onCompare,
  isCompared,
}: RelatedPatentDossierCardProps) {
  const reasons = useMemo(
    () => buildRelationshipReasons(rel, profileAreas, profileAuthority),
    [rel, profileAreas, profileAuthority],
  );
  const profileAreaNames = useMemo(
    () => new Set(profileAreas.map((a) => a.area_name.toLowerCase())),
    [profileAreas],
  );
  const sharedAreas = rel.candidate_application_areas.filter((area) =>
    profileAreaNames.has(area.toLowerCase()),
  );

  return (
    <li
      className={`related-card${isCompared ? " related-card--compared" : ""}`}
    >
      <header className="related-card__head">
        <div className="related-card__title-row">
          <Link
            className="related-card__title"
            to={`/patents/${encodeAnalysisId(rel.analysis_id)}`}
          >
            {rel.title || rel.patent_id}
          </Link>
          {rel.same_technology_group ? (
            <Badge variant="success" withDot>
              Same technology group
            </Badge>
          ) : (
            rel.target_technology_group && (
              <Badge variant="neutral">Cross technology group</Badge>
            )
          )}
        </div>
        <div className="related-card__meta">
          <span className="patent-card__id">{rel.patent_id}</span>
          {rel.assignee && <span>{rel.assignee}</span>}
          {rel.country && <span>{rel.country}</span>}
          {rel.year && <span>{rel.year}</span>}
          <span className="chip chip--authority related-card__authority">
            {rel.source_authority || rel.source}
          </span>
        </div>
      </header>

      <div className="related-card__meters">
        <RelationshipStrengthMeter
          label={rel.relationship_strength}
          score={rel.similarity_score}
          caption="Text-vector similarity."
        />
        <RelationshipStrengthMeter
          label={rel.overlap_signal}
          score={rel.overlap_score}
          caption="Similarity-based overlap signal."
          compact
        />
      </div>

      {(rel.target_technology_group || rel.source_technology_group) && (
        <div className="related-card__group">
          <span className="related-card__group-label">Technology group</span>
          <span className="related-card__group-value">
            {rel.target_technology_group ||
              rel.source_technology_group ||
              "—"}
          </span>
        </div>
      )}

      {rel.shared_keywords.length > 0 && (
        <SharedEvidenceChips
          label="Shared technical signals"
          items={rel.shared_keywords}
          variant="keyword"
          max={8}
        />
      )}

      {rel.candidate_application_areas.length > 0 && (
        <SharedEvidenceChips
          label={
            sharedAreas.length > 0
              ? `Candidate application areas (${sharedAreas.length} shared with this dossier)`
              : "Candidate application areas"
          }
          items={rel.candidate_application_areas}
          variant="area"
          max={6}
        />
      )}

      <details className="related-card__reason">
        <summary>
          <span className="related-card__reason-trigger">Why related?</span>
          <span className="related-card__reason-trigger-hint">
            {reasons.headline}
          </span>
        </summary>
        <ul className="related-card__reason-list">
          {reasons.items.map((item) => (
            <li key={item.key} className="related-card__reason-item">
              <span className="related-card__reason-icon" aria-hidden="true">
                {item.icon}
              </span>
              <div>
                <span className="related-card__reason-title">{item.title}</span>
                <p className="related-card__reason-body">{item.body}</p>
              </div>
            </li>
          ))}
        </ul>
        {rel.explanation && (
          <p className="related-card__reason-footnote">{rel.explanation}</p>
        )}
      </details>

      <div className="related-card__actions">
        <Link
          className="button button--ghost button--sm"
          to={`/patents/${encodeAnalysisId(rel.analysis_id)}`}
        >
          Open dossier →
        </Link>
        <Link
          className="link-button"
          to={`/map?focus=${encodeAnalysisId(rel.analysis_id)}`}
        >
          View neighborhood on Map →
        </Link>
        <button
          type="button"
          className={`button button--sm${
            isCompared ? "" : " button--accent"
          }`}
          onClick={() => onCompare(rel.analysis_id)}
          aria-pressed={isCompared}
        >
          {isCompared ? "✓ In side-by-side review" : "Compare with this patent"}
        </button>
      </div>
    </li>
  );
}
