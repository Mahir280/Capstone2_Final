export interface LandscapeNode {
  analysis_id: string;
  patent_id: string;
  source: string;
  source_authority: string;
  title: string;
  assignee: string | null;
  country: string | null;
  technology_group_id: number | null;
  technology_group: string;
  degree: number;
  x: number;
  y: number;
  candidate_application_areas: string[];
  selected: boolean;
}

export interface LandscapeEdge {
  source_analysis_id: string;
  target_analysis_id: string;
  relationship_strength: string;
  similarity_score: number;
}

export interface LandscapeGroupApplicationArea {
  area_name: string;
  score: number;
  evidence_level: string;
  matched_terms: string[];
  label: string;
}

export interface LandscapeTechnologyGroup {
  technology_group_id: number;
  technology_group: string;
  group_label: string;
  patent_count: number;
  grouping_quality: string;
  grouping_quality_score: number | null;
  top_terms: string[];
  representative_titles: string[];
  candidate_application_areas: LandscapeGroupApplicationArea[];
}

export interface LandscapeSettings {
  relationship_threshold?: number;
  top_k?: number;
  technology_group_count?: number;
  max_edges?: number;
  min_application_score?: number;
  focused?: boolean;
  [key: string]: unknown;
}

export interface LandscapeActiveFilters {
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

export interface LandscapeResponse {
  nodes: LandscapeNode[];
  edges: LandscapeEdge[];
  node_count: number;
  edge_count: number;
  technology_group_count: number;
  average_relationships: number;
  selected_analysis_id: string | null;
  settings: LandscapeSettings;
  technology_groups: LandscapeTechnologyGroup[];
  technology_group_assignments: Record<string, number>;
  grouping_quality_score: number | null;
  warnings: string[];
  total_records_before_filter: number | null;
  total_records_after_filter: number | null;
  active_filters: LandscapeActiveFilters;
}

export interface LandscapeQuery {
  relationship_threshold?: number;
  top_k?: number;
  technology_group_count?: number;
  max_edges?: number;
  min_application_score?: number;
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
