import type { LandscapeActiveFilters } from "./landscape";

export type CountMap = Record<string, number>;
export type CrossTab = Record<string, Record<string, number>>;

export interface CorpusAnalytics {
  by_source: CountMap;
  by_country: CountMap;
  source_country: CrossTab;
}

export interface TrendAnalytics {
  by_publication_year: CountMap;
  by_filing_year: CountMap;
  source_by_year: CrossTab;
}

export interface AssigneeAnalytics {
  top: CountMap;
  by_source: CrossTab;
  by_application_area: CrossTab;
}

export interface TechnologyAnalytics {
  top_keywords: CountMap;
  application_areas: CountMap;
  classifications: CountMap;
  keyword_application_area: CrossTab;
}

export interface QualityAnalytics {
  missing_by_field: CountMap;
  field_completeness_pct: Record<string, number>;
  completeness_score: number;
}

export interface AnalyticsResponse {
  corpus: CorpusAnalytics;
  trends: TrendAnalytics;
  assignees: AssigneeAnalytics;
  technology: TechnologyAnalytics;
  quality: QualityAnalytics;
  total_records_before_filter: number;
  total_records_after_filter: number;
  active_filters: LandscapeActiveFilters;
  warnings: string[];
}

// Analytics shares the same filter surface as the landscape endpoint, minus the
// landscape-specific graph tuning params (threshold, top_k, etc.).
export interface AnalyticsQuery {
  source?: string[];
  publication_year_from?: number;
  publication_year_to?: number;
  filing_year_from?: number;
  filing_year_to?: number;
  country?: string[];
  assignee?: string;
  keyword?: string;
  application_area?: string;
  classification?: string;
}
