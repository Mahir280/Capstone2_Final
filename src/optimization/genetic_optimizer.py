"""Genetic Algorithm optimization for TF-IDF KMeans clustering quality."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from random import Random
from statistics import fmean

from src.clustering.kmeans_clusterer import (
    KMeansClusteringResult,
    KMeansPatentClusterer,
)
from src.features.tfidf import TfidfFeatureService
from src.models.patent import PatentRecord

INVALID_FITNESS = -2.0
DEFAULT_MAX_FEATURE_OPTIONS: tuple[int | None, ...] = (50, 100, 250, 500, 1000, None)
DEFAULT_NGRAM_UPPER_BOUNDS: tuple[int, ...] = (1, 2)


@dataclass(frozen=True, slots=True)
class GeneticClusteringConfig:
    """Small GA chromosome for clustering-related parameters."""

    n_clusters: int
    tfidf_max_features: int | None = None
    ngram_upper_bound: int = 1

    @property
    def ngram_range(self) -> tuple[int, int]:
        """Return the TF-IDF ngram range represented by this chromosome."""
        return (1, self.ngram_upper_bound)


@dataclass(slots=True)
class GeneticGenerationSummary:
    """Best and average fitness information for one GA generation."""

    generation: int
    best_score: float | None
    average_score: float | None


@dataclass(slots=True)
class GeneticOptimizationResult:
    """Structured output from a GA clustering optimization run."""

    best_config: GeneticClusteringConfig | None
    best_score: float | None
    baseline_score: float | None
    improvement_over_baseline: float | None
    generation_history: list[GeneticGenerationSummary]
    warnings: list[str] = field(default_factory=list)
    optimized_assignments: dict[str, int] = field(default_factory=dict)
    optimized_cluster_sizes: dict[int, int] = field(default_factory=dict)
    optimized_top_terms_per_cluster: dict[int, list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class _EvaluatedConfig:
    config: GeneticClusteringConfig
    fitness: float
    score: float | None
    clustering_result: KMeansClusteringResult | None
    warnings: list[str] = field(default_factory=list)


class GeneticClusteringOptimizer:
    """Optimize TF-IDF KMeans clustering quality with a small deterministic GA."""

    def __init__(
        self,
        *,
        population_size: int = 8,
        generations: int = 5,
        mutation_rate: float = 0.2,
        random_state: int = 42,
        max_feature_options: Sequence[int | None] | None = None,
        ngram_upper_bounds: Sequence[int] | None = None,
    ) -> None:
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.random_state = random_state
        self.max_feature_options = tuple(
            DEFAULT_MAX_FEATURE_OPTIONS
            if max_feature_options is None
            else max_feature_options
        )
        self.ngram_upper_bounds = tuple(
            DEFAULT_NGRAM_UPPER_BOUNDS
            if ngram_upper_bounds is None
            else ngram_upper_bounds
        )
        self.tfidf_service = TfidfFeatureService()
        self.clusterer = KMeansPatentClusterer(random_state=random_state)

    def optimize(
        self,
        records: list[PatentRecord],
        *,
        baseline_cluster_count: int = 3,
        top_terms_per_cluster: int = 8,
    ) -> GeneticOptimizationResult:
        """Run GA optimization and compare the best score with a baseline."""
        warnings: list[str] = []
        baseline_score = self._baseline_score(
            records,
            baseline_cluster_count,
            top_terms_per_cluster,
            warnings,
        )

        if len(records) < 3:
            warnings.append(
                "At least 3 patents are required for GA clustering optimization "
                "because silhouette scoring needs more than 2 samples."
            )
            return self._empty_result(baseline_score, warnings)

        population_size = self._bounded_population_size(warnings)
        generations = self._bounded_generations(warnings)
        mutation_rate = self._bounded_mutation_rate(warnings)
        if generations == 0:
            warnings.append("GA optimization did not run because generations is 0.")
            return self._empty_result(baseline_score, warnings)

        cluster_options = self._cluster_options(len(records))
        max_feature_options = self._option_tuple(
            self.max_feature_options,
            fallback=(None,),
            label="TF-IDF max feature",
            warnings=warnings,
        )
        ngram_options = self._option_tuple(
            self.ngram_upper_bounds,
            fallback=DEFAULT_NGRAM_UPPER_BOUNDS,
            label="ngram upper-bound",
            warnings=warnings,
        )

        rng = Random(self.random_state)
        population = [
            self._random_config(
                rng,
                cluster_options,
                max_feature_options,
                ngram_options,
            )
            for _ in range(population_size)
        ]

        best_evaluation: _EvaluatedConfig | None = None
        history: list[GeneticGenerationSummary] = []

        for generation in range(1, generations + 1):
            evaluations = [
                self._evaluate_config(
                    records,
                    config,
                    top_terms_per_cluster=top_terms_per_cluster,
                )
                for config in population
            ]

            for evaluation in evaluations:
                self._extend_unique(warnings, evaluation.warnings)

            generation_best = max(evaluations, key=lambda item: item.fitness)
            valid_scores = [
                evaluation.score
                for evaluation in evaluations
                if evaluation.score is not None
            ]
            history.append(
                GeneticGenerationSummary(
                    generation=generation,
                    best_score=generation_best.score,
                    average_score=fmean(valid_scores) if valid_scores else None,
                )
            )

            if generation_best.score is not None and (
                best_evaluation is None
                or best_evaluation.score is None
                or generation_best.score > best_evaluation.score
            ):
                best_evaluation = generation_best

            if generation < generations:
                population = self._next_population(
                    evaluations,
                    rng,
                    population_size,
                    mutation_rate,
                    cluster_options,
                    max_feature_options,
                    ngram_options,
                )

        if best_evaluation is None or best_evaluation.clustering_result is None:
            warnings.append("No valid GA configurations produced a silhouette score.")
            return GeneticOptimizationResult(
                best_config=None,
                best_score=None,
                baseline_score=baseline_score,
                improvement_over_baseline=None,
                generation_history=history,
                warnings=warnings,
            )

        best_result = best_evaluation.clustering_result
        best_score = best_evaluation.score
        improvement = (
            best_score - baseline_score
            if best_score is not None and baseline_score is not None
            else None
        )

        return GeneticOptimizationResult(
            best_config=best_evaluation.config,
            best_score=best_score,
            baseline_score=baseline_score,
            improvement_over_baseline=improvement,
            generation_history=history,
            warnings=warnings,
            optimized_assignments=best_result.assignments,
            optimized_cluster_sizes=best_result.cluster_sizes,
            optimized_top_terms_per_cluster=best_result.top_terms_by_cluster,
        )

    def _baseline_score(
        self,
        records: list[PatentRecord],
        baseline_cluster_count: int,
        top_terms_per_cluster: int,
        warnings: list[str],
    ) -> float | None:
        tfidf_result = self.tfidf_service.build_from_patents(records)
        baseline_result = self.clusterer.cluster(
            records,
            tfidf_result,
            baseline_cluster_count,
            top_terms_per_cluster=top_terms_per_cluster,
        )
        self._extend_unique(
            warnings,
            [f"Baseline: {warning}" for warning in baseline_result.warnings],
        )
        return baseline_result.silhouette_score

    def _evaluate_config(
        self,
        records: list[PatentRecord],
        config: GeneticClusteringConfig,
        *,
        top_terms_per_cluster: int,
    ) -> _EvaluatedConfig:
        warnings = self._configuration_warnings(config, len(records))
        if warnings:
            return _EvaluatedConfig(
                config=config,
                fitness=INVALID_FITNESS,
                score=None,
                clustering_result=None,
                warnings=warnings,
            )

        try:
            tfidf_result = self.tfidf_service.build_from_patents(
                records,
                max_features=config.tfidf_max_features,
                ngram_range=config.ngram_range,
            )
            clustering_result = self.clusterer.cluster(
                records,
                tfidf_result,
                config.n_clusters,
                top_terms_per_cluster=top_terms_per_cluster,
            )
        except ValueError as exc:
            return _EvaluatedConfig(
                config=config,
                fitness=INVALID_FITNESS,
                score=None,
                clustering_result=None,
                warnings=[f"GA configuration skipped safely: {exc}"],
            )

        if not tfidf_result.is_valid:
            return _EvaluatedConfig(
                config=config,
                fitness=INVALID_FITNESS,
                score=None,
                clustering_result=clustering_result,
                warnings=[
                    f"GA TF-IDF features are not available: {tfidf_result.error}"
                ],
            )

        if clustering_result.silhouette_score is None:
            return _EvaluatedConfig(
                config=config,
                fitness=INVALID_FITNESS,
                score=None,
                clustering_result=clustering_result,
                warnings=clustering_result.warnings,
            )

        return _EvaluatedConfig(
            config=config,
            fitness=clustering_result.silhouette_score,
            score=clustering_result.silhouette_score,
            clustering_result=clustering_result,
            warnings=clustering_result.warnings,
        )

    def _configuration_warnings(
        self,
        config: GeneticClusteringConfig,
        sample_count: int,
    ) -> list[str]:
        warnings: list[str] = []
        if config.n_clusters < 2:
            warnings.append("GA configuration skipped: n_clusters must be at least 2.")
        if config.n_clusters >= sample_count:
            warnings.append(
                "GA configuration skipped: n_clusters must be less than the "
                "number of patents for silhouette scoring."
            )
        if config.tfidf_max_features is not None and config.tfidf_max_features < 1:
            warnings.append(
                "GA configuration skipped: tfidf_max_features must be positive "
                "or None."
            )
        if config.ngram_upper_bound not in (1, 2):
            warnings.append(
                "GA configuration skipped: ngram_upper_bound must be 1 or 2."
            )
        return warnings

    def _next_population(
        self,
        evaluations: list[_EvaluatedConfig],
        rng: Random,
        population_size: int,
        mutation_rate: float,
        cluster_options: tuple[int, ...],
        max_feature_options: tuple[int | None, ...],
        ngram_options: tuple[int, ...],
    ) -> list[GeneticClusteringConfig]:
        ranked = sorted(evaluations, key=lambda item: item.fitness, reverse=True)
        parent_count = max(1, len(ranked) // 2)
        parents = [evaluation.config for evaluation in ranked[:parent_count]]

        next_population = [ranked[0].config]
        while len(next_population) < population_size:
            parent_a = rng.choice(parents)
            parent_b = rng.choice(parents)
            child = self._crossover(parent_a, parent_b, rng)
            if rng.random() < mutation_rate:
                child = self._mutate(
                    child,
                    rng,
                    cluster_options,
                    max_feature_options,
                    ngram_options,
                )
            next_population.append(child)

        return next_population

    def _crossover(
        self,
        parent_a: GeneticClusteringConfig,
        parent_b: GeneticClusteringConfig,
        rng: Random,
    ) -> GeneticClusteringConfig:
        return GeneticClusteringConfig(
            n_clusters=rng.choice([parent_a.n_clusters, parent_b.n_clusters]),
            tfidf_max_features=rng.choice(
                [parent_a.tfidf_max_features, parent_b.tfidf_max_features]
            ),
            ngram_upper_bound=rng.choice(
                [parent_a.ngram_upper_bound, parent_b.ngram_upper_bound]
            ),
        )

    def _mutate(
        self,
        config: GeneticClusteringConfig,
        rng: Random,
        cluster_options: tuple[int, ...],
        max_feature_options: tuple[int | None, ...],
        ngram_options: tuple[int, ...],
    ) -> GeneticClusteringConfig:
        gene = rng.choice(["n_clusters", "tfidf_max_features", "ngram_upper_bound"])
        if gene == "n_clusters":
            return GeneticClusteringConfig(
                n_clusters=rng.choice(cluster_options),
                tfidf_max_features=config.tfidf_max_features,
                ngram_upper_bound=config.ngram_upper_bound,
            )
        if gene == "tfidf_max_features":
            return GeneticClusteringConfig(
                n_clusters=config.n_clusters,
                tfidf_max_features=rng.choice(max_feature_options),
                ngram_upper_bound=config.ngram_upper_bound,
            )
        return GeneticClusteringConfig(
            n_clusters=config.n_clusters,
            tfidf_max_features=config.tfidf_max_features,
            ngram_upper_bound=rng.choice(ngram_options),
        )

    def _random_config(
        self,
        rng: Random,
        cluster_options: tuple[int, ...],
        max_feature_options: tuple[int | None, ...],
        ngram_options: tuple[int, ...],
    ) -> GeneticClusteringConfig:
        return GeneticClusteringConfig(
            n_clusters=rng.choice(cluster_options),
            tfidf_max_features=rng.choice(max_feature_options),
            ngram_upper_bound=rng.choice(ngram_options),
        )

    def _cluster_options(self, sample_count: int) -> tuple[int, ...]:
        upper_bound = min(8, sample_count - 1)
        return tuple(range(2, upper_bound + 1))

    def _bounded_population_size(self, warnings: list[str]) -> int:
        if self.population_size < 2:
            warnings.append("Population size was adjusted to 2 for GA selection.")
            return 2
        return self.population_size

    def _bounded_generations(self, warnings: list[str]) -> int:
        if self.generations < 1:
            warnings.append("Generations must be at least 1 for GA optimization.")
            return 0
        return self.generations

    def _bounded_mutation_rate(self, warnings: list[str]) -> float:
        if self.mutation_rate < 0:
            warnings.append("Mutation rate was adjusted to 0.0.")
            return 0.0
        if self.mutation_rate > 1:
            warnings.append("Mutation rate was adjusted to 1.0.")
            return 1.0
        return self.mutation_rate

    def _option_tuple(
        self,
        values: Sequence[object],
        *,
        fallback: tuple[object, ...],
        label: str,
        warnings: list[str],
    ) -> tuple:
        unique_values = tuple(dict.fromkeys(values))
        if unique_values:
            return unique_values
        warnings.append(f"No {label} options were provided; fallback options are used.")
        return fallback

    def _empty_result(
        self,
        baseline_score: float | None,
        warnings: list[str],
    ) -> GeneticOptimizationResult:
        return GeneticOptimizationResult(
            best_config=None,
            best_score=None,
            baseline_score=baseline_score,
            improvement_over_baseline=None,
            generation_history=[],
            warnings=warnings,
        )

    def _extend_unique(self, target: list[str], values: list[str]) -> None:
        for value in values:
            if value not in target:
                target.append(value)
