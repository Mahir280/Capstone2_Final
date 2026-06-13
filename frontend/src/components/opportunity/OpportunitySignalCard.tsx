import { Badge } from "../common/Badge";
import {
  type OpportunitySignal,
  getSignalTierMeta,
} from "./types";

interface OpportunitySignalCardProps {
  signal: OpportunitySignal;
}

export function OpportunitySignalCard({ signal }: OpportunitySignalCardProps) {
  const tierMeta = getSignalTierMeta(signal.tier);
  return (
    <li
      className={`opportunity-card opportunity-card--${signal.tier} opportunity-card--${signal.category}`}
      aria-label={`Opportunity signal: ${signal.title} (${tierMeta.label}).`}
    >
      <header className="opportunity-card__head">
        <span className="opportunity-card__category">
          {signal.categoryLabel}
        </span>
        <Badge variant={tierMeta.variant} withDot>
          {tierMeta.label}
        </Badge>
      </header>

      <h3 className="opportunity-card__title">{signal.title}</h3>

      <p className="opportunity-card__rationale">{signal.rationale}</p>

      {signal.evidence.length > 0 && (
        <ul className="opportunity-card__evidence">
          {signal.evidence.map((row) => (
            <li
              key={`${row.label}-${row.value}`}
              className="opportunity-card__evidence-row"
            >
              <span className="opportunity-card__evidence-label">
                {row.label}
              </span>
              <span className="opportunity-card__evidence-value">
                {row.value}
              </span>
            </li>
          ))}
        </ul>
      )}

      {signal.limitations.length > 0 && (
        <footer className="opportunity-card__limitations">
          {signal.limitations.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </footer>
      )}
    </li>
  );
}
