export interface DataSourceStatusResponse {
  has_patents: boolean;
  total_patents: number;
  database_path: string;
  database_exists: boolean;
  prepared_dataset_path: string;
  prepared_dataset_available: boolean;
  sample_dataset_path: string;
  sample_dataset_available: boolean;
  source_authority_counts: Record<string, number>;
  import_method_counts: Record<string, number>;
  source_counts: Record<string, number>;
  assignee_count: number;
  year_range: string;
  processed_runtime_files: string[];
  status_message: string;
  warnings: string[];
}

export interface DataSourceLoadSummary {
  source?: string;
  dataset_kind?: string;
  total_raw_rows?: number;
  valid_normalized_rows?: number;
  skipped_rows?: number;
  upserted_rows?: number;
  source_counts?: Record<string, number>;
  message?: string;
  warnings?: string[];
  errors?: string[];
  [key: string]: unknown;
}

export interface DataSourceLoadResponse {
  status: string;
  message: string;
  summary: DataSourceLoadSummary;
  warnings: string[];
}
