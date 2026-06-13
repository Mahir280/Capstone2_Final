import { SectionCard } from "../common/SectionCard";
import type {
  ProfileApplicationArea,
  RelatedPatent,
} from "../../types/patents";
import { APPLICATION_SIGNAL_LEGEND } from "./ApplicationSignalBadge";
import { CandidateApplicationAreaCard } from "./CandidateApplicationAreaCard";

interface CandidateApplicationAreasPanelProps {
  areas: ProfileApplicationArea[];
  related: RelatedPatent[];
}

export function CandidateApplicationAreasPanel({
  areas,
  related,
}: CandidateApplicationAreasPanelProps) {
  if (areas.length === 0) return null;

  return (
    <SectionCard
      title="Candidate application areas"
      description="Technical signal, not a guaranteed market classification."
    >
      <div className="candidate-area-intro">
        <p className="candidate-area-intro__text">
          Suggested from matched terms, relationship context, and technology
          group fit.
        </p>
        <ul
          className="candidate-area-legend"
          aria-label="What the signal labels mean"
        >
          {APPLICATION_SIGNAL_LEGEND.map((info) => (
            <li
              key={info.tier}
              className={`candidate-area-legend__item candidate-area-legend__item--${info.tier}`}
            >
              <span
                className={`candidate-area-legend__dot candidate-area-legend__dot--${info.tier}`}
                aria-hidden="true"
              />
              <span className="candidate-area-legend__label">{info.label}</span>
              <span className="candidate-area-legend__desc">
                {info.description}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <ul className="candidate-area-grid">
        {areas.map((area) => (
          <CandidateApplicationAreaCard
            key={area.area_name}
            area={area}
            related={related}
          />
        ))}
      </ul>
    </SectionCard>
  );
}
