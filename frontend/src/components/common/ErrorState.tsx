import { Callout } from "./Callout";

interface ErrorStateProps {
  title?: string;
  message: string;
  hint?: string;
}

export function ErrorState({
  title = "Could not load data",
  message,
  hint,
}: ErrorStateProps) {
  return (
    <Callout variant="error" title={title} role="alert">
      <p>{message}</p>
      {hint && <p style={{ marginTop: "0.35rem" }}>{hint}</p>}
    </Callout>
  );
}
