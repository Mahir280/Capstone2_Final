interface KeywordChipsProps {
  keywords: string[];
  max?: number;
}

export function KeywordChips({ keywords, max = 8 }: KeywordChipsProps) {
  if (keywords.length === 0) return null;
  const visible = keywords.slice(0, max);
  const remaining = keywords.length - visible.length;
  return (
    <div className="chip-row" aria-label="Technical keywords">
      {visible.map((keyword) => (
        <span key={keyword} className="chip chip--keyword">
          {keyword}
        </span>
      ))}
      {remaining > 0 && <span className="chip">+{remaining} more</span>}
    </div>
  );
}
