export interface PatentCard {
  analysis_id: string;
  patent_id: string;
  source: string;
  source_authority: string;
  import_method: string;
  title: string;
  abstract_preview: string;
  assignee: string | null;
  country: string | null;
  year: string | null;
  keywords: string[];
  candidate_application_areas: string[];
  match_label: string;
  match_score: number;
  source_url: string | null;
}

export interface PatentSearchResponse {
  query: string;
  total_results: number;
  returned_results: number;
  filters: Record<string, string>;
  patents: PatentCard[];
  warnings: string[];
  limit: number | null;
  offset: number;
}

export interface RelatedPatent {
  analysis_id: string;
  patent_id: string;
  source: string;
  source_authority: string;
  title: string;
  assignee: string | null;
  country: string | null;
  year: string | null;
  relationship_strength: string;
  similarity_score: number;
  overlap_signal: string;
  overlap_score: number;
  same_technology_group: boolean;
  source_technology_group_id: number | null;
  target_technology_group_id: number | null;
  source_technology_group: string;
  target_technology_group: string;
  shared_keywords: string[];
  candidate_application_areas: string[];
  explanation: string;
}

export interface ProfileTopTerm {
  term: string;
  importance: string;
  score: number;
}

export interface ProfileApplicationArea {
  area_name: string;
  score: number;
  evidence_level: string;
  matched_terms: string[];
  evidence_count: number;
  explanation: string;
}

export interface MetadataRow {
  Field: string;
  Value: string;
}

export interface PatentProfile {
  analysis_id: string;
  patent_id: string;
  source: string;
  source_authority: string;
  import_method: string;
  title: string;
  abstract: string;
  plain_language_summary: string;
  assignee: string | null;
  inventors: string[];
  publication_date: string | null;
  filing_date: string | null;
  year: string | null;
  country: string | null;
  language: string | null;
  source_url: string | null;
  keywords: string[];
  ipc_codes: string[];
  cpc_codes: string[];
  claims_preview: string | null;
  top_terms: ProfileTopTerm[];
  candidate_application_areas: ProfileApplicationArea[];
  related_patents: RelatedPatent[];
  metadata_rows: MetadataRow[];
  advanced_metadata_rows: MetadataRow[];
  warnings: string[];
}

export interface RelatedPatentsResponse {
  analysis_id: string;
  related_patents: RelatedPatent[];
  warnings: string[];
}

export interface FilterOptionsResponse {
  sources: string[];
  source_counts: Record<string, number>;
  assignees: string[];
  top_assignees: Record<string, number>;
  countries: string[];
  country_counts: Record<string, number>;
  years: string[];
  publication_year_range: {
    min: number | null;
    max: number | null;
  };
  filing_year_range: {
    min: number | null;
    max: number | null;
  };
  top_keywords: Record<string, number>;
  top_application_areas: Record<string, number>;
  classifications: string[];
  top_classifications: Record<string, number>;
  technology_groups: string[];
  candidate_application_areas: string[];
}

export const ALL_FILTER_VALUE = "All";

export interface PatentSearchParams {
  q?: string;
  source?: string;
  assignee?: string;
  country?: string;
  year?: string;
  limit?: number;
  offset?: number;
}

export interface PatentListParams {
  limit?: number;
  offset?: number;
}

export function isFilterActive(params: PatentSearchParams): boolean {
  const q = (params.q ?? "").trim();
  if (q.length > 0) return true;
  const filterKeys: Array<keyof PatentSearchParams> = [
    "source",
    "assignee",
    "country",
    "year",
  ];
  return filterKeys.some((key) => {
    const value = params[key];
    return typeof value === "string" && value !== "" && value !== ALL_FILTER_VALUE;
  });
}
