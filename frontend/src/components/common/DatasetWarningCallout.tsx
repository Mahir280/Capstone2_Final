import { Callout } from "./Callout";
import { WarningList } from "./WarningList";

interface DatasetWarningCalloutProps {
  warnings: string[];
  title?: string;
}

export function DatasetWarningCallout({
  warnings,
  title = "Dataset coverage notes",
}: DatasetWarningCalloutProps) {
  if (warnings.length === 0) return null;

  return (
    <Callout variant="warning" title={title}>
      <WarningList warnings={warnings} />
    </Callout>
  );
}

