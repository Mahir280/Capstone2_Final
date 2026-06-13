"""Tests for the Genetic Algorithm clustering optimizer."""

from src.models.enums import SourceType
from src.models.patent import PatentRecord
from src.optimization import GeneticClusteringOptimizer


def test_optimizer_returns_result_on_valid_small_dataset() -> None:
    optimizer = GeneticClusteringOptimizer(
        population_size=6,
        generations=3,
        mutation_rate=0.2,
        random_state=7,
    )

    result = optimizer.optimize(_optimization_records(), baseline_cluster_count=2)

    assert result.best_config is not None
    assert result.best_score is not None
    assert result.baseline_score is not None
    assert result.optimized_assignments
    assert result.optimized_cluster_sizes
    assert result.optimized_top_terms_per_cluster


def test_result_includes_best_config_and_score_or_safe_warning() -> None:
    optimizer = GeneticClusteringOptimizer(
        population_size=4,
        generations=2,
        mutation_rate=0.1,
        random_state=3,
    )

    result = optimizer.optimize(_optimization_records(), baseline_cluster_count=2)

    assert (result.best_config is not None and result.best_score is not None) or (
        result.best_config is None and result.best_score is None and result.warnings
    )


def test_optimizer_uses_analysis_id_based_assignments() -> None:
    records = _duplicate_patent_id_records()
    optimizer = GeneticClusteringOptimizer(
        population_size=4,
        generations=2,
        mutation_rate=0.2,
        random_state=9,
    )

    result = optimizer.optimize(records, baseline_cluster_count=2)

    assert set(result.optimized_assignments) == {
        record.analysis_id for record in records
    }
    assert "DUPLICATE-1" not in result.optimized_assignments
    assert "CSV_IMPORT:DUPLICATE-1" in result.optimized_assignments
    assert "JSON_IMPORT:DUPLICATE-1" in result.optimized_assignments


def test_optimizer_handles_too_few_patents_safely() -> None:
    optimizer = GeneticClusteringOptimizer(
        population_size=4,
        generations=2,
        mutation_rate=0.2,
        random_state=5,
    )

    result = optimizer.optimize(_optimization_records()[:2], baseline_cluster_count=2)

    assert result.best_config is None
    assert result.best_score is None
    assert result.generation_history == []
    assert result.optimized_assignments == {}
    assert any("At least 3 patents" in warning for warning in result.warnings)


def test_optimizer_is_deterministic_with_fixed_random_state() -> None:
    records = _optimization_records()

    result_a = GeneticClusteringOptimizer(
        population_size=6,
        generations=3,
        mutation_rate=0.2,
        random_state=11,
    ).optimize(records, baseline_cluster_count=2)
    result_b = GeneticClusteringOptimizer(
        population_size=6,
        generations=3,
        mutation_rate=0.2,
        random_state=11,
    ).optimize(records, baseline_cluster_count=2)

    assert result_a.best_config == result_b.best_config
    assert result_a.best_score == result_b.best_score
    assert result_a.generation_history == result_b.generation_history
    assert result_a.optimized_assignments == result_b.optimized_assignments


def test_invalid_configurations_do_not_crash() -> None:
    optimizer = GeneticClusteringOptimizer(
        population_size=4,
        generations=2,
        mutation_rate=0.2,
        random_state=13,
        max_feature_options=(0,),
        ngram_upper_bounds=(3,),
    )

    result = optimizer.optimize(_optimization_records(), baseline_cluster_count=2)

    assert result.best_config is None
    assert result.best_score is None
    assert len(result.generation_history) == 2
    assert any("GA configuration skipped" in warning for warning in result.warnings)
    assert any("No valid GA configurations" in warning for warning in result.warnings)


def test_generation_history_length_matches_requested_generations() -> None:
    generations = 4
    optimizer = GeneticClusteringOptimizer(
        population_size=5,
        generations=generations,
        mutation_rate=0.2,
        random_state=17,
    )

    result = optimizer.optimize(_optimization_records(), baseline_cluster_count=2)

    assert len(result.generation_history) == generations
    assert [item.generation for item in result.generation_history] == [1, 2, 3, 4]


def _optimization_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="US-FIBER-1",
            source=SourceType.CSV_IMPORT,
            title="Fiber strain sensor garment",
            abstract="fiber textile strain sensor wearable thread garment",
            keywords=["fiber", "sensor", "textile"],
        ),
        PatentRecord(
            patent_id="US-FIBER-2",
            source=SourceType.CSV_IMPORT,
            title="Knitted textile pressure sensor",
            abstract="knitted fiber pressure sensor wearable fabric textile",
            keywords=["fiber", "pressure", "sensor"],
        ),
        PatentRecord(
            patent_id="US-POWER-1",
            source=SourceType.JSON_IMPORT,
            title="Flexible battery textile",
            abstract="battery storage cell energy flexible wearable power",
            keywords=["battery", "energy", "storage"],
        ),
        PatentRecord(
            patent_id="US-POWER-2",
            source=SourceType.JSON_IMPORT,
            title="Yarn power module",
            abstract="power cell battery storage yarn flexible electronics",
            keywords=["battery", "power", "cell"],
        ),
        PatentRecord(
            patent_id="US-ANTENNA-1",
            source=SourceType.CSV_IMPORT,
            title="Conductive yarn antenna",
            abstract="antenna wireless signal conductive yarn textile communication",
            keywords=["antenna", "wireless", "yarn"],
        ),
        PatentRecord(
            patent_id="US-ANTENNA-2",
            source=SourceType.JSON_IMPORT,
            title="Textile communication antenna",
            abstract="wireless antenna conductive fabric signal wearable textile",
            keywords=["antenna", "signal", "conductive"],
        ),
    ]


def _duplicate_patent_id_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="DUPLICATE-1",
            source=SourceType.CSV_IMPORT,
            title="Fiber sensor garment",
            abstract="fiber sensor textile wearable thread",
            keywords=["fiber"],
        ),
        PatentRecord(
            patent_id="DUPLICATE-1",
            source=SourceType.JSON_IMPORT,
            title="Flexible battery pack",
            abstract="battery storage cell power wearable",
            keywords=["battery"],
        ),
        PatentRecord(
            patent_id="US-FIBER-UNIQUE",
            source=SourceType.CSV_IMPORT,
            title="Textile strain monitor",
            abstract="fiber textile sensor strain wearable",
            keywords=["sensor"],
        ),
        PatentRecord(
            patent_id="US-BATTERY-UNIQUE",
            source=SourceType.JSON_IMPORT,
            title="Textile power module",
            abstract="battery power storage cell textile",
            keywords=["power"],
        ),
    ]
