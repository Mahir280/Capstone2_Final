import type { ReactNode } from "react";
import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { encodeAnalysisId, getPatentProfile } from "../../api/patents";
import type {
  PatentProfile,
  ProfileApplicationArea,
  RelatedPatent,
} from "../../types/patents";
import { ApiError } from "../../api/client";
import { LoadingState } from "../common/LoadingState";
import { ErrorState } from "../common/ErrorState";
import { RelationshipStrengthMeter } from "./RelationshipStrengthMeter";

const UNAVAILABLE = "Not available in this corpus record";

function describeText(value: string | null | undefined): ReactNode {
  if (!value || value.trim().length === 0) {
    return <span className="comparison-panel__missing">{UNAVAILABLE}</span>;
  }
  return value;
}

function describeAreas(items: string[]): ReactNode {
  if (items.length === 0) {
    return <span className="comparison-panel__missing">{UNAVAILABLE}</span>;
  }
  return (
    <div className="chip-row">
      {items.slice(0, 6).map((item) => (
        <span key={item} className="chip chip--area">
          {item}
        </span>
      ))}
      {items.length > 6 && (
        <span className="chip chip--muted">+{items.length - 6} more</span>
      )}
    </div>
  );
}

function profileAreaNames(areas: ProfileApplicationArea[]): string[] {
  return areas.map((area) => area.area_name);
}

interface PatentComparisonPanelProps {
  currentProfile: PatentProfile;
  related: RelatedPatent;
  onClose: () => void;
}

export function PatentComparisonPanel({
  currentProfile,
  related,
  onClose,
}: PatentComparisonPanelProps) {
  const relatedProfileQuery = useQuery({
    queryKey: ["patent-profile", related.analysis_id],
    queryFn: ({ signal }) => getPatentProfile(related.analysis_id, signal),
    enabled: related.analysis_id.length > 0,
  });

  const relatedProfile = relatedProfileQuery.data;
  const isPending = relatedProfileQuery.isPending;
  const errorState = relatedProfileQuery.isError ? relatedProfileQuery.error : null;

  const sharedKeywordsSet = useMemo(
    () => new Set(related.shared_keywords.map((k) => k.toLowerCase())),
    [related.shared_keywords],
  );

  const currentKeywords = currentProfile.keywords;
  const relatedKeywords = relatedProfile?.keywords ?? [];
  const currentAreas = profileAreaNames(currentProfile.candidate_application_areas);
  const relatedAreas = relatedProfile
    ? profileAreaNames(relatedProfile.candidate_application_areas)
    : related.candidate_application_areas;

  const sharedAreas = useMemo(() => {
    const currentLower = new Set(currentAreas.map((a) => a.toLowerCase()));
    return relatedAreas.filter((a) => currentLower.has(a.toLowerCase()));
  }, [currentAreas, relatedAreas]);

  function renderKeywordCell(items: string[]): ReactNode {
    if (items.length === 0) {
      return <span className="comparison-panel__missing">{UNAVAILABLE}</span>;
    }
    return (
      <div className="chip-row">
        {items.slice(0, 10).map((item) => {
          const isShared = sharedKeywordsSet.has(item.toLowerCase());
          return (
            <span
              key={item}
              className={`chip chip--keyword${
                isShared ? " chip--shared" : ""
              }`}
              title={isShared ? "Shared technical signal" : undefined}
            >
              {isShared && (
                <span className="chip__dot" aria-hidden="true">
                  ★
                </span>
              )}
              {item}
            </span>
          );
        })}
        {items.length > 10 && (
          <span className="chip chip--muted">+{items.length - 10} more</span>
        )}
      </div>
    );
  }

  const rows: Array<{
    key: string;
    label: string;
    current: ReactNode;
    other: ReactNode;
  }> = [
    {
      key: "patent_id",
      label: "Patent ID",
      current: (
        <span className="patent-card__id">{currentProfile.patent_id}</span>
      ),
      other: <span className="patent-card__id">{related.patent_id}</span>,
    },
    {
      key: "source",
      label: "Source authority",
      current: describeText(
        currentProfile.source_authority || currentProfile.source,
      ),
      other: describeText(related.source_authority || related.source),
    },
    {
      key: "year",
      label: "Year / publication",
      current: describeText(
        currentProfile.publication_date || currentProfile.year,
      ),
      other: describeText(
        relatedProfile?.publication_date ?? relatedProfile?.year ?? related.year,
      ),
    },
    {
      key: "assignee",
      label: "Assignee / applicant",
      current: describeText(currentProfile.assignee),
      other: describeText(relatedProfile?.assignee ?? related.assignee),
    },
    {
      key: "country",
      label: "Jurisdiction",
      current: describeText(currentProfile.country),
      other: describeText(relatedProfile?.country ?? related.country),
    },
    {
      key: "tech-group",
      label: "Technology group",
      current: describeText(related.source_technology_group),
      other: describeText(related.target_technology_group),
    },
    {
      key: "areas",
      label: "Candidate application areas",
      current: describeAreas(currentAreas),
      other: describeAreas(relatedAreas),
    },
    {
      key: "keywords",
      label: "Technical signals (★ = shared)",
      current: renderKeywordCell(currentKeywords),
      other: renderKeywordCell(relatedKeywords),
    },
  ];

  return (
    <section
      className="comparison-panel"
      role="region"
      aria-labelledby="comparison-panel-title"
    >
      <header className="comparison-panel__head">
        <div>
          <span className="comparison-panel__eyebrow">
            Side-by-side relationship review
          </span>
          <h3 id="comparison-panel-title" className="comparison-panel__title">
            Technical/context comparison
          </h3>
          <p className="comparison-panel__intro">
            Reading aid that places this dossier patent next to a selected
            related patent using only fields available in the current corpus.
            This is not a legal or freedom-to-operate comparison.
          </p>
        </div>
        <button
          type="button"
          className="button button--ghost button--sm"
          onClick={onClose}
          aria-label="Close side-by-side review"
        >
          Close review ✕
        </button>
      </header>

      <div className="comparison-panel__strength">
        <RelationshipStrengthMeter
          label={related.relationship_strength}
          score={related.similarity_score}
          caption="Relationship strength between the two patents."
        />
        <RelationshipStrengthMeter
          label={related.overlap_signal}
          score={related.overlap_score}
          caption="Overlap signal — how much technical surface area appears shared."
          compact
        />
        {related.same_technology_group && (
          <p className="comparison-panel__note">
            Both patents sit in the same technology group from the current
            corpus grouping.
          </p>
        )}
        {sharedAreas.length > 0 && (
          <p className="comparison-panel__note">
            Shared candidate application areas: {sharedAreas.slice(0, 5).join(", ")}
            {sharedAreas.length > 5 ? ", …" : ""}.
          </p>
        )}
      </div>

      {isPending && (
        <LoadingState message="Loading related patent profile for side-by-side review..." />
      )}
      {errorState && (
        <ErrorState
          title="Could not load related patent for comparison"
          message={
            errorState instanceof ApiError
              ? errorState.detail
              : String(errorState)
          }
          hint="The basic relationship signals are still shown above; full profile fields could not be loaded."
        />
      )}

      <div className="comparison-panel__grid" role="table">
        <div className="comparison-panel__row comparison-panel__row--header" role="row">
          <div className="comparison-panel__cell comparison-panel__cell--label" role="columnheader">
            Field
          </div>
          <div className="comparison-panel__cell comparison-panel__cell--current" role="columnheader">
            <span className="comparison-panel__col-eyebrow">This dossier</span>
            <span className="comparison-panel__col-title">
              {currentProfile.title || currentProfile.patent_id}
            </span>
          </div>
          <div className="comparison-panel__cell comparison-panel__cell--other" role="columnheader">
            <span className="comparison-panel__col-eyebrow">Related patent</span>
            <span className="comparison-panel__col-title">
              {related.title || related.patent_id}
            </span>
          </div>
        </div>

        {rows.map((row) => (
          <div key={row.key} className="comparison-panel__row" role="row">
            <div className="comparison-panel__cell comparison-panel__cell--label" role="rowheader">
              {row.label}
            </div>
            <div className="comparison-panel__cell" role="cell">
              {row.current}
            </div>
            <div className="comparison-panel__cell" role="cell">
              {row.other}
            </div>
          </div>
        ))}
      </div>

      {related.explanation && (
        <div className="comparison-panel__explanation">
          <span className="comparison-panel__col-eyebrow">
            Relationship explanation
          </span>
          <p>{related.explanation}</p>
        </div>
      )}

      <footer className="comparison-panel__footer">
        <Link
          className="button button--sm"
          to={`/patents/${encodeAnalysisId(related.analysis_id)}`}
        >
          Open related dossier →
        </Link>
        <Link
          className="link-button"
          to={`/map?focus=${encodeAnalysisId(related.analysis_id)}`}
        >
          View neighborhood on Map →
        </Link>
        <span className="comparison-panel__footnote">
          Side-by-side review uses only fields already available in the loaded
          corpus. Missing fields are marked as “{UNAVAILABLE}”.
        </span>
      </footer>
    </section>
  );
}
