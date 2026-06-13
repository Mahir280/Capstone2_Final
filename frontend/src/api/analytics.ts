import { apiGet } from "./client";
import { compactParams } from "./landscape";
import type { AnalyticsQuery, AnalyticsResponse } from "../types/analytics";

function analyticsParams(query: AnalyticsQuery) {
  return compactParams({
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

export function getAnalytics(
  query: AnalyticsQuery = {},
  signal?: AbortSignal,
): Promise<AnalyticsResponse> {
  return apiGet<AnalyticsResponse>(
    "/api/analytics",
    analyticsParams(query),
    signal,
  );
}
