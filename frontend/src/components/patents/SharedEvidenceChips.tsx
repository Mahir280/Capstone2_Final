interface SharedEvidenceChipsProps {
  label: string;
  items: string[];
  variant?: "keyword" | "area";
  max?: number;
  emptyMessage?: string;
}

export function SharedEvidenceChips({
  label,
  items,
  variant = "keyword",
  max = 8,
  emptyMessage,
}: SharedEvidenceChipsProps) {
  const visible = items.slice(0, max);
  const remaining = items.length - visible.length;
  const chipClass = variant === "area" ? "chip chip--area" : "chip chip--keyword";

  return (
    <div className="shared-evidence">
      <span className="shared-evidence__label">{label}</span>
      {items.length === 0 ? (
        emptyMessage ? (
          <span className="shared-evidence__empty">{emptyMessage}</span>
        ) : null
      ) : (
        <div className="chip-row" aria-label={label}>
          {visible.map((item) => (
            <span key={item} className={chipClass}>
              {item}
            </span>
          ))}
          {remaining > 0 && (
            <span className="chip chip--muted">+{remaining} more</span>
          )}
        </div>
      )}
    </div>
  );
}
