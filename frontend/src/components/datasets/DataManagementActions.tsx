import type { ReactNode } from "react";

import { Badge } from "../common/Badge";
import { SectionCard } from "../common/SectionCard";
import type { DataSourceStatusResponse } from "../../types/dataSources";

type ActionKind = "prepared" | "sample";

interface DataManagementActionsProps {
  status: DataSourceStatusResponse;
  activeAction: ActionKind | null;
  isLoading: boolean;
  onLoadPrepared: () => void;
  onLoadSample: () => void;
}

function describePath(path: string): string {
  if (!path) return "—";
  return path;
}

export function DataManagementActions({
  status,
  activeAction,
  isLoading,
  onLoadPrepared,
  onLoadSample,
}: DataManagementActionsProps) {
  return (
    <SectionCard
      title="Maintainer data actions"
      description="Load or refresh the local corpus."
    >
      <p className="data-actions__note">
        Loading replaces local records and refreshes all corpus views.
      </p>
      <div className="data-actions__grid">
        <ActionCard
          title="Load prepared corpus"
          badge={
            status.prepared_dataset_available ? (
              <Badge variant="success" withDot>
                Available
              </Badge>
            ) : (
              <Badge variant="warning" withDot>
                Missing
              </Badge>
            )
          }
          description="Main curated source-labeled CSV."
          path={status.prepared_dataset_path}
          action={
            <button
              type="button"
              className="button"
              onClick={onLoadPrepared}
              disabled={!status.prepared_dataset_available || isLoading}
              title={
                status.prepared_dataset_available
                  ? undefined
                  : "Prepared corpus file is missing on disk."
              }
            >
              {activeAction === "prepared"
                ? "Loading prepared corpus…"
                : "Load prepared corpus"}
            </button>
          }
        />
        <ActionCard
          title="Load sample corpus (recovery / testing)"
          badge={
            status.sample_dataset_available ? (
              <Badge variant="primary" withDot>
                Available
              </Badge>
            ) : (
              <Badge variant="warning" withDot>
                Missing
              </Badge>
            )
          }
          description="Recovery/testing reload of the canonical corpus."
          path={status.sample_dataset_path}
          action={
            <button
              type="button"
              className="button button--ghost"
              onClick={onLoadSample}
              disabled={!status.sample_dataset_available || isLoading}
              title={
                status.sample_dataset_available
                  ? undefined
                  : "Sample corpus file is missing on disk."
              }
            >
              {activeAction === "sample"
                ? "Loading sample corpus…"
                : "Load sample corpus"}
            </button>
          }
        />
        <ActionCard
          title="Patent-office adapters"
          badge={<Badge variant="neutral">Future work</Badge>}
          description="Reserved for later source-ingestion work."
          path="adapters/* (not active)"
          future
          action={
            <button
              type="button"
              className="button button--ghost"
              disabled
              aria-label="Patent-office adapters are not available in this version"
            >
              Not available
            </button>
          }
        />
      </div>
    </SectionCard>
  );
}

interface ActionCardProps {
  title: string;
  badge: ReactNode;
  description: string;
  path: string;
  action: ReactNode;
  future?: boolean;
}

function ActionCard({
  title,
  badge,
  description,
  path,
  action,
  future,
}: ActionCardProps) {
  const className = future
    ? "data-actions__card data-actions__card--future"
    : "data-actions__card";
  return (
    <article className={className}>
      <div className="data-actions__card-head">
        <h3 className="data-actions__card-title">{title}</h3>
        {badge}
      </div>
      <p className="data-actions__card-description">{description}</p>
      <div className="data-actions__card-path" title={path || undefined}>
        {describePath(path)}
      </div>
      <div className="data-actions__card-action">{action}</div>
    </article>
  );
}
