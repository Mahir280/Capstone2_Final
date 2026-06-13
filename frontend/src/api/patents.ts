import { apiGet } from "./client";
import {
  ALL_FILTER_VALUE,
  type FilterOptionsResponse,
  type PatentListParams,
  type PatentProfile,
  type PatentSearchParams,
  type PatentSearchResponse,
  type RelatedPatentsResponse,
} from "../types/patents";

export function encodeAnalysisId(analysisId: string): string {
  return encodeURIComponent(analysisId);
}

export function getPatents(
  params: PatentListParams = {},
  signal?: AbortSignal,
): Promise<PatentSearchResponse> {
  return apiGet<PatentSearchResponse>(
    "/api/patents",
    {
      limit: params.limit,
      offset: params.offset,
    },
    signal,
  );
}

export function searchPatents(
  params: PatentSearchParams,
  signal?: AbortSignal,
): Promise<PatentSearchResponse> {
  return apiGet<PatentSearchResponse>(
    "/api/patents/search",
    {
      q: params.q ?? "",
      source: params.source ?? ALL_FILTER_VALUE,
      assignee: params.assignee ?? ALL_FILTER_VALUE,
      country: params.country ?? ALL_FILTER_VALUE,
      year: params.year ?? ALL_FILTER_VALUE,
      limit: params.limit,
      offset: params.offset,
    },
    signal,
  );
}

export function getPatentProfile(
  analysisId: string,
  signal?: AbortSignal,
): Promise<PatentProfile> {
  return apiGet<PatentProfile>(
    `/api/patents/${encodeAnalysisId(analysisId)}`,
    undefined,
    signal,
  );
}

export function getRelatedPatents(
  analysisId: string,
  signal?: AbortSignal,
): Promise<RelatedPatentsResponse> {
  return apiGet<RelatedPatentsResponse>(
    `/api/patents/${encodeAnalysisId(analysisId)}/related`,
    undefined,
    signal,
  );
}

export function getFilterOptions(
  signal?: AbortSignal,
): Promise<FilterOptionsResponse> {
  return apiGet<FilterOptionsResponse>("/api/filters", undefined, signal);
}
