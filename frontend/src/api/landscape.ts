import { apiGet } from "./client";
import type { QueryValue } from "./client";
import type { FilterOptionsResponse } from "../types/patents";
import type { LandscapeQuery, LandscapeResponse } from "../types/landscape";

export function compactParams(params: Record<string, QueryValue>) {
  const compacted: Record<string, QueryValue> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (typeof value === "string" && value.trim() === "") continue;
    if (Array.isArray(value)) {
      const items = value.filter(
        (item) =>
          item !== undefined &&
          item !== null &&
          !(typeof item === "string" && item.trim() === ""),
      );
      if (items.length === 0) continue;
      compacted[key] = items;
      continue;
    }
    compacted[key] = value;
  }
  return compacted;
}

function landscapeParams(query: LandscapeQuery) {
  return compactParams({
    relationship_threshold: query.relationship_threshold,
    top_k: query.top_k,
    technology_group_count: query.technology_group_count,
    max_edges: query.max_edges,
    min_application_score: query.min_application_score,
    source: query.source,
    publication_year_from: query.publication_year_from,
    publication_year_to: query.publication_year_to,
    filing_year_from: query.filing_year_from,
    filing_year_to: query.filing_year_to,
    country: query.country,
    assignee: query.assignee,
    keyword: query.keyword,
    application_area: query.application_area,
    classification: query.classification,
  });
}

export function getLandscape(
  query: LandscapeQuery = {},
  signal?: AbortSignal,
): Promise<LandscapeResponse> {
  return apiGet<LandscapeResponse>(
    "/api/landscape",
    landscapeParams(query),
    signal,
  );
}

export function getFocusedLandscape(
  analysisId: string,
  query: LandscapeQuery = {},
  signal?: AbortSignal,
): Promise<LandscapeResponse> {
  return apiGet<LandscapeResponse>(
    `/api/landscape/focused/${encodeURIComponent(analysisId)}`,
    landscapeParams(query),
    signal,
  );
}

export function getLandscapeFilterOptions(
  signal?: AbortSignal,
): Promise<FilterOptionsResponse> {
  return apiGet<FilterOptionsResponse>("/api/filters", undefined, signal);
}
