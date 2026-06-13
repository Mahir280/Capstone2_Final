import { Link } from "react-router-dom";

import { encodeAnalysisId } from "../../api/patents";
import type { PatentCard as PatentCardData } from "../../types/patents";
import { ApplicationAreaChips } from "./ApplicationAreaChips";
import { KeywordChips } from "./KeywordChips";

interface PatentCardProps {
  patent: PatentCardData;
}

export function PatentCard({ patent }: PatentCardProps) {
  const profileHref = `/patents/${encodeAnalysisId(patent.analysis_id)}`;
  const authority = patent.source_authority || patent.source;
  const metaParts = [
    patent.assignee,
    patent.country,
    patent.year,
  ].filter((part): part is string => Boolean(part));

  const showMatchLabel =
    patent.match_label && patent.match_label !== "Curated record";

  return (
    <article className="patent-card">
      <div className="patent-card__header">
        <h3 className="patent-card__title">
          <Link to={profileHref}>{patent.title || patent.patent_id}</Link>
        </h3>
        {authority && (
          <span className="chip chip--authority">{authority}</span>
        )}
      </div>

      <div className="patent-card__meta">
        <span className="patent-card__meta-item">
          <span className="patent-card__id">{patent.patent_id}</span>
        </span>
        {metaParts.map((part) => (
          <span key={part} className="patent-card__meta-item">
            {part}
          </span>
        ))}
      </div>

      {patent.abstract_preview && (
        <p className="patent-card__preview">{patent.abstract_preview}</p>
      )}

      {patent.keywords.length > 0 && (
        <div className="patent-card__row">
          <span className="patent-card__row-label">Technical keywords</span>
          <KeywordChips keywords={patent.keywords} />
        </div>
      )}

      {patent.candidate_application_areas.length > 0 && (
        <div className="patent-card__row">
          <div className="patent-card__row-header">
            <span className="patent-card__row-label">
              Candidate application areas
            </span>
            <span
              className="patent-card__row-hint"
              title="Technical signals, not guaranteed market classifications."
            >
              reading aids
            </span>
          </div>
          <ApplicationAreaChips areas={patent.candidate_application_areas} />
        </div>
      )}

      <div className="patent-card__footer">
        {showMatchLabel ? (
          <span className="patent-card__match">
            <strong>Match signal:</strong> {patent.match_label}
          </span>
        ) : (
          <span />
        )}
        <Link className="link-button" to={profileHref}>
          Open dossier →
        </Link>
      </div>
    </article>
  );
}
