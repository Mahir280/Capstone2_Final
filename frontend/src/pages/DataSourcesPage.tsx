import { useState } from "react";
import { Link } from "react-router-dom";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { ApiError } from "../api/client";
import {
  getDataSourceStatus,
  loadPreparedDataset,
  loadSampleRecoveryCorpus,
} from "../api/dataSources";
import { Badge } from "../components/common/Badge";
import { Callout } from "../components/common/Callout";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { PageHeader } from "../components/common/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { WarningList } from "../components/common/WarningList";
import { DataManagementActions } from "../components/datasets/DataManagementActions";
import { DatasetCoverageStatus } from "../components/datasets/DatasetCoverageStatus";
import { SourceCoveragePanel } from "../components/datasets/SourceCoveragePanel";
import type {
  DataSourceLoadResponse,
  DataSourceStatusResponse,
} from "../types/dataSources";

type ActionKind = "prepared" | "sample";

interface ActionFeedback {
  kind: "success" | "error";
  title: string;
  message: string;
  summary?: DataSourceLoadResponse;
}

export function DataSourcesPage() {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<ActionFeedback | null>(null);
  const [activeAction, setActiveAction] = useState<ActionKind | null>(null);

  const statusQuery = useQuery({
    queryKey: ["data-sources", "status"],
    queryFn: ({ signal }) => getDataSourceStatus(signal),
  });

  const invalidateDataConsumers = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["data-sources", "status"] }),
      queryClient.invalidateQueries({ queryKey: ["insights"] }),
      queryClient.invalidateQueries({ queryKey: ["patents"] }),
      queryClient.invalidateQueries({ queryKey: ["filter-options"] }),
    ]);
  };

  const handleLoadResult = async (
    response: DataSourceLoadResponse,
    actionLabel: string,
  ) => {
    const upserted =
      typeof response.summary.upserted_rows === "number"
        ? response.summary.upserted_rows
        : undefined;
    const valid =
      typeof response.summary.valid_normalized_rows === "number"
        ? response.summary.valid_normalized_rows
        : undefined;
    const detail =
      upserted !== undefined
        ? `${upserted} record${upserted === 1 ? "" : "s"} stored locally${
            valid !== undefined ? ` (from ${valid} valid rows).` : "."
          }`
        : "Local store refreshed.";
    setFeedback({
      kind: "success",
      title: `${actionLabel}: ${response.message}`,
      message: detail,
      summary: response,
    });
    await invalidateDataConsumers();
  };

  const handleError = (error: unknown, actionLabel: string) => {
    if (error instanceof ApiError) {
      if (error.status === 404) {
        setFeedback({
          kind: "error",
          title: `${actionLabel}: dataset file not found`,
          message: error.detail,
        });
        return;
      }
      setFeedback({
        kind: "error",
        title: `${actionLabel} failed`,
        message: error.detail,
      });
      return;
    }
    setFeedback({
      kind: "error",
      title: `${actionLabel} failed`,
      message: error instanceof Error ? error.message : String(error),
    });
  };

  const preparedMutation = useMutation({
    mutationFn: () => loadPreparedDataset(),
    onMutate: () => {
      setActiveAction("prepared");
      setFeedback(null);
    },
    onSuccess: (response) =>
      handleLoadResult(response, "Load prepared corpus"),
    onError: (error) => handleError(error, "Load prepared corpus"),
    onSettled: () => setActiveAction(null),
  });

  const sampleMutation = useMutation({
    mutationFn: () => loadSampleRecoveryCorpus(),
    onMutate: () => {
      setActiveAction("sample");
      setFeedback(null);
    },
    onSuccess: (response) => handleLoadResult(response, "Load sample corpus"),
    onError: (error) => handleError(error, "Load sample corpus"),
    onSettled: () => setActiveAction(null),
  });

  const isLoading = activeAction !== null || statusQuery.isFetching;

  return (
    <section>
      <PageHeader
        eyebrow="Data & Methods"
        title="Corpus & Sources"
        description={
          <>
            Loaded corpus status, source coverage, and project evidence.
          </>
        }
        actions={
          <>
            <Link className="link-button" to="/">
              Open Overview
            </Link>
            <Link className="link-button" to="/analytics">
              Open Trends &amp; Players
            </Link>
          </>
        }
        meta={
          <>
            <Badge variant="primary" withDot>
              Curated source-labeled corpus
            </Badge>
            <Badge variant="neutral">Bounded coverage</Badge>
            <Badge variant="accent">No live patent-office connection</Badge>
          </>
        }
      />

      {statusQuery.isPending && (
        <LoadingState message="Loading corpus and source status..." />
      )}

      {statusQuery.isError && (
        <ErrorState
          message={
            statusQuery.error instanceof ApiError
              ? statusQuery.error.detail
              : String(statusQuery.error)
          }
          hint="Make sure the FastAPI backend is running at the configured VITE_API_BASE_URL."
        />
      )}

      {statusQuery.isSuccess && (
        <DataSourceBody
          status={statusQuery.data}
          activeAction={activeAction}
          isLoading={isLoading}
          onRefreshStatus={() => statusQuery.refetch()}
          onLoadPrepared={() => preparedMutation.mutate()}
          onLoadSample={() => sampleMutation.mutate()}
        />
      )}

      {feedback && (
        <FeedbackBanner
          feedback={feedback}
          onDismiss={() => setFeedback(null)}
        />
      )}
    </section>
  );
}

interface DataSourceBodyProps {
  status: DataSourceStatusResponse;
  activeAction: ActionKind | null;
  isLoading: boolean;
  onRefreshStatus: () => void;
  onLoadPrepared: () => void;
  onLoadSample: () => void;
}

function DataSourceBody({
  status,
  activeAction,
  isLoading,
  onRefreshStatus,
  onLoadPrepared,
  onLoadSample,
}: DataSourceBodyProps) {
  return (
    <>
      <DatasetCoverageStatus
        status={status}
        isLoading={isLoading}
        onRefresh={onRefreshStatus}
      />

      <Callout variant="info" title="Corpus boundaries">
        <p>
          Curated source-labeled corpus only. No live patent-office coverage or
          legal conclusions.
        </p>
      </Callout>

      <SourceCoveragePanel
        counts={status.source_authority_counts}
        total={status.total_patents}
      />

      {(status.status_message || status.warnings.length > 0) && (
        <SectionCard
          title="Corpus status notes"
          description="Latest backend status and corpus warnings."
        >
          {status.status_message && (
            <p className="coverage-status-notes__message">
              {status.status_message}
            </p>
          )}
          {status.warnings.length > 0 && (
            <>
              <span className="coverage-status-notes__label">Warnings</span>
              <WarningList warnings={status.warnings} />
            </>
          )}
        </SectionCard>
      )}

      <DataManagementActions
        status={status}
        activeAction={activeAction}
        isLoading={isLoading}
        onLoadPrepared={onLoadPrepared}
        onLoadSample={onLoadSample}
      />
    </>
  );
}

function FeedbackBanner({
  feedback,
  onDismiss,
}: {
  feedback: ActionFeedback;
  onDismiss: () => void;
}) {
  return (
    <Callout
      variant={feedback.kind === "success" ? "success" : "error"}
      title={feedback.title}
      actions={
        <>
          {feedback.kind === "success" && (
            <>
              <Link className="link-button" to="/">
                Open Overview
              </Link>
              <Link className="link-button" to="/analytics">
                Open Trends &amp; Players
              </Link>
            </>
          )}
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={onDismiss}
          >
            Dismiss
          </button>
        </>
      }
    >
      <p>{feedback.message}</p>
      {feedback.kind === "success" &&
        feedback.summary &&
        feedback.summary.warnings.length > 0 && (
          <WarningList warnings={feedback.summary.warnings} />
        )}
    </Callout>
  );
}
