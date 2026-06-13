import type { ReactNode } from "react";

interface StatTileProps {
  classNamePrefix: string;
  label: ReactNode;
  value: ReactNode;
  subValue?: ReactNode;
  hint?: ReactNode;
  primary?: boolean;
}

export function StatTile({
  classNamePrefix,
  label,
  value,
  subValue,
  hint,
  primary = false,
}: StatTileProps) {
  const base = `${classNamePrefix}__stat`;
  const className = primary ? `${base} ${base}--primary` : base;

  return (
    <div className={className}>
      <span className={`${classNamePrefix}__label`}>{label}</span>
      <span className={`${classNamePrefix}__value`}>
        {value}
        {subValue && (
          <span className={`${classNamePrefix}__sub`}>{subValue}</span>
        )}
      </span>
      {hint && <span className={`${classNamePrefix}__hint`}>{hint}</span>}
    </div>
  );
}

