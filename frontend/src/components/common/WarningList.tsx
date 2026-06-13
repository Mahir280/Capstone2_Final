interface WarningListProps {
  warnings: string[];
  ariaLabel?: string;
}

export function WarningList({
  warnings,
  ariaLabel = "Dataset coverage warnings",
}: WarningListProps) {
  if (warnings.length === 0) return null;

  return (
    <ul className="warnings-list" aria-label={ariaLabel}>
      {warnings.map((warning) => (
        <li key={warning}>{warning}</li>
      ))}
    </ul>
  );
}

