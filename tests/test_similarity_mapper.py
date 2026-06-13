"""Tests for the TF-IDF patent similarity mapper."""

from collections import Counter

from scipy.sparse import csr_matrix

from src.clustering.similarity_mapper import (
    PatentSimilarityResult,
    TfidfSimilarityMapper,
)
from src.features.tfidf import TfidfFeatureResult
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_similarity_mapper_produces_edges_for_valid_small_dataset() -> None:
    records = _threshold_records()
    result = _map_with_rows(
        records,
        rows=[
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        similarity_threshold=0.5,
        top_k=10,
    )

    assert result.edge_count == 2
    assert result.patents_analyzed == 3
    assert result.threshold == 0.5
    assert result.top_k == 10
    assert not result.warnings


def test_similarity_mapper_uses_analysis_id_not_patent_id_only() -> None:
    records = _duplicate_patent_id_records()
    result = _map_with_rows(
        records,
        rows=[
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        similarity_threshold=0.5,
        top_k=10,
    )

    edge = result.edges[0]

    assert {
        edge.source_analysis_id,
        edge.target_analysis_id,
    } == {"CSV_IMPORT:DUPLICATE-1", "JSON_IMPORT:DUPLICATE-1"}
    assert edge.source_analysis_id != edge.source_patent_id
    assert edge.target_analysis_id != edge.target_patent_id


def test_duplicate_patent_id_with_different_sources_does_not_collapse() -> None:
    records = _duplicate_patent_id_records()
    result = _map_with_rows(
        records,
        rows=[
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        similarity_threshold=0.5,
        top_k=10,
    )

    assert result.patents_analyzed == 3
    assert result.edge_count == 1
    assert result.edges[0].source_patent_id == "DUPLICATE-1"
    assert result.edges[0].target_patent_id == "DUPLICATE-1"


def test_similarity_mapper_does_not_produce_self_edges() -> None:
    result = _map_with_rows(
        _duplicate_patent_id_records(),
        rows=[
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        similarity_threshold=0.5,
        top_k=10,
    )

    assert all(
        edge.source_analysis_id != edge.target_analysis_id for edge in result.edges
    )


def test_similarity_mapper_avoids_duplicate_undirected_edges() -> None:
    result = _map_with_rows(
        _threshold_records(),
        rows=[
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        similarity_threshold=0.5,
        top_k=10,
    )

    unordered_pairs = [
        frozenset((edge.source_analysis_id, edge.target_analysis_id))
        for edge in result.edges
    ]

    assert len(unordered_pairs) == len(set(unordered_pairs))


def test_similarity_mapper_respects_threshold() -> None:
    records = _threshold_records()
    rows = [
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ]

    low_threshold_result = _map_with_rows(
        records,
        rows=rows,
        similarity_threshold=0.5,
        top_k=10,
    )
    high_threshold_result = _map_with_rows(
        records,
        rows=rows,
        similarity_threshold=0.75,
        top_k=10,
    )

    assert low_threshold_result.edge_count == 2
    assert high_threshold_result.edges == []
    assert any("threshold" in warning for warning in high_threshold_result.warnings)


def test_similarity_mapper_respects_top_k() -> None:
    records = _threshold_records()
    result = _map_with_rows(
        records,
        rows=[
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [1.0, 0.0, 1.0],
        ],
        similarity_threshold=0.1,
        top_k=1,
    )

    relationship_counts: Counter[str] = Counter()
    for edge in result.edges:
        relationship_counts[edge.source_analysis_id] += 1
        relationship_counts[edge.target_analysis_id] += 1

    assert result.edge_count == 1
    assert all(count <= 1 for count in relationship_counts.values())


def test_similarity_mapper_handles_fewer_than_two_patents_safely() -> None:
    records = [
        PatentRecord(
            patent_id="US-SINGLE-1",
            source=SourceType.CSV_IMPORT,
            title="Single fiber sensor",
            abstract="fiber sensor textile",
            keywords=["fiber"],
        )
    ]
    result = _map_with_rows(
        records,
        rows=[[1.0, 0.0]],
        similarity_threshold=0.1,
        top_k=5,
    )

    assert result.edges == []
    assert result.patents_analyzed == 1
    assert result.warnings == [
        "At least 2 patents are required for similarity mapping."
    ]


def test_similarity_mapper_edge_scores_are_between_zero_and_one() -> None:
    result = _map_with_rows(
        _threshold_records(),
        rows=[
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        similarity_threshold=0.5,
        top_k=10,
    )

    assert result.edges
    assert all(0.0 <= edge.similarity_score <= 1.0 for edge in result.edges)


def _map_with_rows(
    records: list[PatentRecord],
    *,
    rows: list[list[float]],
    similarity_threshold: float,
    top_k: int,
) -> PatentSimilarityResult:
    tfidf_result = _tfidf_result(records, rows)
    return TfidfSimilarityMapper().map_relationships(
        records,
        tfidf_result,
        similarity_threshold=similarity_threshold,
        top_k=top_k,
    )


def _tfidf_result(
    records: list[PatentRecord],
    rows: list[list[float]],
) -> TfidfFeatureResult:
    matrix = csr_matrix(rows)
    return TfidfFeatureResult(
        analysis_ids=[record.analysis_id for record in records],
        patent_ids=[record.patent_id for record in records],
        matrix_shape=matrix.shape,
        feature_names=[f"term_{index}" for index in range(matrix.shape[1])],
        matrix=matrix,
    )


def _threshold_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="US-FIBER-1",
            source=SourceType.CSV_IMPORT,
            title="Fiber sensor garment",
            abstract="fiber sensor textile wearable",
            keywords=["fiber"],
        ),
        PatentRecord(
            patent_id="US-HYBRID-1",
            source=SourceType.CSV_IMPORT,
            title="Hybrid textile sensor",
            abstract="fiber sensor battery textile",
            keywords=["sensor"],
        ),
        PatentRecord(
            patent_id="US-BATTERY-1",
            source=SourceType.JSON_IMPORT,
            title="Flexible battery pack",
            abstract="battery storage cell power",
            keywords=["battery"],
        ),
    ]


def _duplicate_patent_id_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="DUPLICATE-1",
            source=SourceType.CSV_IMPORT,
            title="Fiber sensor garment",
            abstract="fiber sensor textile wearable",
            keywords=["fiber"],
        ),
        PatentRecord(
            patent_id="DUPLICATE-1",
            source=SourceType.JSON_IMPORT,
            title="Fiber sensor garment alternate",
            abstract="fiber sensor textile wearable",
            keywords=["sensor"],
        ),
        PatentRecord(
            patent_id="US-BATTERY-1",
            source=SourceType.JSON_IMPORT,
            title="Flexible battery pack",
            abstract="battery storage cell power",
            keywords=["battery"],
        ),
    ]
