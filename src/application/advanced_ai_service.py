"""Application service for Genetic Algorithm result DTO assembly."""

from src.application._formatting import technology_group_label
from src.application.dto import AdvancedAIResultDTO
from src.models.patent import PatentRecord
from src.optimization import GeneticClusteringOptimizer, GeneticOptimizationResult


class AdvancedAIService:
    """Run optional GA optimization and serialize its result."""

    def run_optimization(
        self,
        records: list[PatentRecord],
        *,
        baseline_cluster_count: int = 3,
        population_size: int = 8,
        generations: int = 5,
        mutation_rate: float = 0.2,
        random_state: int = 42,
    ) -> AdvancedAIResultDTO:
        """Return a structured GA result or a safe not-runnable response."""
        settings = {
            "baseline_cluster_count": int(baseline_cluster_count),
            "population_size": int(population_size),
            "generations": int(generations),
            "mutation_rate": float(mutation_rate),
            "random_state": int(random_state),
        }
        if len(records) < 3:
            return AdvancedAIResultDTO(
                runnable=False,
                status_message=(
                    "At least 3 saved patents are required before Advanced AI "
                    "optimization can run."
                ),
                settings=settings,
                warnings=[
                    "At least 3 patents are required for GA clustering optimization."
                ],
            )

        optimizer = GeneticClusteringOptimizer(
            population_size=population_size,
            generations=generations,
            mutation_rate=mutation_rate,
            random_state=random_state,
        )
        result = optimizer.optimize(
            records,
            baseline_cluster_count=baseline_cluster_count,
        )
        return self.from_result(result, settings=settings)

    def from_result(
        self,
        result: GeneticOptimizationResult,
        *,
        settings: dict[str, int | float],
    ) -> AdvancedAIResultDTO:
        """Serialize an optimizer result without exposing optimizer internals."""
        best_config = None
        if result.best_config is not None:
            best_config = {
                "technology_group_count": result.best_config.n_clusters,
                "keyword_evidence_feature_limit": (
                    "None"
                    if result.best_config.tfidf_max_features is None
                    else result.best_config.tfidf_max_features
                ),
                "keyword_phrase_upper_bound": result.best_config.ngram_upper_bound,
            }

        runnable = result.best_config is not None and result.best_score is not None
        return AdvancedAIResultDTO(
            runnable=runnable,
            status_message=self._status_message(result),
            settings=settings,
            baseline_score=result.baseline_score,
            best_score=result.best_score,
            improvement_over_baseline=result.improvement_over_baseline,
            best_config=best_config,
            generation_history=[
                {
                    "generation": item.generation,
                    "best_score": item.best_score,
                    "average_score": item.average_score,
                }
                for item in result.generation_history
            ],
            optimized_assignments=dict(result.optimized_assignments),
            optimized_cluster_sizes={
                technology_group_label(cluster_id): count
                for cluster_id, count in sorted(result.optimized_cluster_sizes.items())
            },
            optimized_top_terms_per_cluster={
                technology_group_label(cluster_id): list(terms)
                for cluster_id, terms in sorted(
                    result.optimized_top_terms_per_cluster.items()
                )
            },
            warnings=list(result.warnings),
        )

    def _status_message(self, result: GeneticOptimizationResult) -> str:
        if result.best_config is None or result.best_score is None:
            return (
                "Advanced AI optimization completed safely, but no valid optimized "
                "technology grouping was produced."
            )
        if (
            result.improvement_over_baseline is not None
            and result.improvement_over_baseline > 0
        ):
            return (
                "Advanced AI optimization found a stronger tested technology "
                "grouping configuration."
            )
        return (
            "Advanced AI optimization ran successfully, with no clear improvement "
            "over the standard grouping in this run."
        )
