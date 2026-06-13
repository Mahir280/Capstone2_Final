import { apiGet, apiPost } from "./client";
import type {
  DataSourceLoadResponse,
  DataSourceStatusResponse,
} from "../types/dataSources";

export function getDataSourceStatus(
  signal?: AbortSignal,
): Promise<DataSourceStatusResponse> {
  return apiGet<DataSourceStatusResponse>(
    "/api/data-sources/status",
    undefined,
    signal,
  );
}

export function loadPreparedDataset(
  signal?: AbortSignal,
): Promise<DataSourceLoadResponse> {
  return apiPost<DataSourceLoadResponse>(
    "/api/data-sources/load-prepared",
    undefined,
    signal,
  );
}

export function loadSampleRecoveryCorpus(
  signal?: AbortSignal,
): Promise<DataSourceLoadResponse> {
  return apiPost<DataSourceLoadResponse>(
    "/api/data-sources/load-demo",
    undefined,
    signal,
  );
}
