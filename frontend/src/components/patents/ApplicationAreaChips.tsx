interface ApplicationAreaChipsProps {
  areas: string[];
  max?: number;
}

export function ApplicationAreaChips({
  areas,
  max = 6,
}: ApplicationAreaChipsProps) {
  if (areas.length === 0) return null;
  const visible = areas.slice(0, max);
  const remaining = areas.length - visible.length;
  return (
    <div className="chip-row" aria-label="Candidate application areas">
      {visible.map((area) => (
        <span key={area} className="chip chip--area">
          {area}
        </span>
      ))}
      {remaining > 0 && <span className="chip">+{remaining} more</span>}
    </div>
  );
}
