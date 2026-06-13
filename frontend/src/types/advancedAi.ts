export interface AdvancedAIRequest {
  baseline_cluster_count?: number;
  population_size?: number;
  generations?: number;
  mutation_rate?: number;
  random_state?: number;
}

export interface AdvancedAIBestConfig {
  technology_group_count?: number;
  keyword_evidence_feature_limit?: number | string;
  keyword_phrase_upper_bound?: number;
  [key: string]: unknown;
}

export interface AdvancedAIGenerationEntry {
  generation: number;
  best_score: number | null;
  average_score: number | null;
  [key: string]: unknown;
}

export interface AdvancedAIResult {
  runnable: boolean;
  status_message: string;
  settings: Record<string, number>;
  baseline_score: number | null;
  best_score: number | null;
  improvement_over_baseline: number | null;
  best_config: AdvancedAIBestConfig | null;
  generation_history: AdvancedAIGenerationEntry[];
  optimized_assignments: Record<string, number>;
  optimized_cluster_sizes: Record<string, number>;
  optimized_top_terms_per_cluster: Record<string, string[]>;
  warnings: string[];
}

export const ADVANCED_AI_DEFAULTS: Required<AdvancedAIRequest> = {
  baseline_cluster_count: 3,
  population_size: 8,
  generations: 5,
  mutation_rate: 0.2,
  random_state: 42,
};

export const ADVANCED_AI_LIMITS = {
  baseline_cluster_count: { min: 2, max: 20, step: 1 },
  population_size: { min: 2, max: 50, step: 1 },
  generations: { min: 1, max: 50, step: 1 },
  mutation_rate: { min: 0, max: 1, step: 0.05 },
  random_state: { min: 0, max: 999_999, step: 1 },
} as const;
