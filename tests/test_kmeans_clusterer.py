"""Tests for the baseline KMeans patent clusterer."""

from src.clustering.kmeans_clusterer import KMeansPatentClusterer
from src.features.tfidf import TfidfFeatureResult, TfidfFeatureService
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_kmeans_clustering_works_on_small_valid_dataset() -> None:
    records = _sample_cluster_records()
    tfidf_result = _tfidf_result(records)

    result = KMeansPatentClusterer(random_state=7).cluster(
        records, tfidf_result, requested_cluster_count=2
    )

    assert len(result.assignments) == len(records)
    assert result.selected_cluster_count == 2
    assert result.actual_cluster_count == 2
    assert result.silhouette_score is not None
    assert len(result.summaries) == 2
    assert all(summary.top_terms for summary in result.summaries)


def test_kmeans_result_uses_analysis_ids_for_assignments() -> None:
    records = _sample_cluster_records()
    tfidf_result = _tfidf_result(records)

    result = KMeansPatentClusterer().cluster(
        records, tfidf_result, requested_cluster_count=2
    )

    assert set(result.assignments) == {record.analysis_id for record in records}
    assert "US-FIBER-1" not in result.assignments


def test_duplicate_patent_ids_from_different_sources_do_not_collapse() -> None:
    records = _duplicate_patent_id_records()
    tfidf_result = _tfidf_result(records)

    result = KMeansPatentClusterer().cluster(
        records, tfidf_result, requested_cluster_count=2
    )

    assert len(result.assignments) == len(records)
    assert "CSV_IMPORT:DUPLICATE-1" in result.assignments
    assert "JSON_IMPORT:DUPLICATE-1" in result.assignments
    assert "DUPLICATE-1" not in result.assignments


def test_invalid_cluster_count_is_adjusted_safely() -> None:
    records = _sample_cluster_records()
    tfidf_result = _tfidf_result(records)

    result = KMeansPatentClusterer().cluster(
        records, tfidf_result, requested_cluster_count=99
    )

    assert result.requested_cluster_count == 99
    assert result.selected_cluster_count == len(records) - 1
    assert len(result.assignments) == len(records)
    assert any("adjusted" in warning for warning in result.warnings)


def test_silhouette_score_is_none_when_cluster_count_is_invalid() -> None:
    records = _sample_cluster_records()
    tfidf_result = _tfidf_result(records)

    result = KMeansPatentClusterer().cluster(
        records, tfidf_result, requested_cluster_count=1
    )

    assert result.selected_cluster_count == 1
    assert result.silhouette_score is None
    assert any(
        "Silhouette score is unavailable" in warning for warning in result.warnings
    )


def test_cluster_sizes_sum_to_input_patent_count() -> None:
    records = _sample_cluster_records()
    tfidf_result = _tfidf_result(records)

    result = KMeansPatentClusterer().cluster(
        records, tfidf_result, requested_cluster_count=2
    )

    assert sum(result.cluster_sizes.values()) == len(records)


def test_single_patent_input_returns_warning_without_crashing() -> None:
    records = [
        PatentRecord(
            patent_id="US-SINGLE-1",
            source=SourceType.CSV_IMPORT,
            title="Fiber sensor garment",
            abstract="fiber sensor textile wearable",
            keywords=["fiber"],
        )
    ]
    tfidf_result = _tfidf_result(records)

    result = KMeansPatentClusterer().cluster(
        records, tfidf_result, requested_cluster_count=2
    )

    assert result.assignments == {}
    assert result.selected_cluster_count == 0
    assert result.silhouette_score is None
    assert result.warnings == ["At least 2 patents are required for KMeans clustering."]


def _tfidf_result(records: list[PatentRecord]) -> TfidfFeatureResult:
    return TfidfFeatureService().build_from_patents(records)


def _sample_cluster_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="US-FIBER-1",
            source=SourceType.CSV_IMPORT,
            title="Fiber sensor garment",
            abstract="fiber sensor textile wearable thread",
            keywords=["fiber", "sensor"],
        ),
        PatentRecord(
            patent_id="US-FIBER-2",
            source=SourceType.CSV_IMPORT,
            title="Textile strain monitor",
            abstract="fiber textile sensor strain wearable",
            keywords=["thread", "sensor"],
        ),
        PatentRecord(
            patent_id="US-BATTERY-1",
            source=SourceType.JSON_IMPORT,
            title="Flexible battery pack",
            abstract="battery storage cell power wearable",
            keywords=["battery", "storage"],
        ),
        PatentRecord(
            patent_id="US-BATTERY-2",
            source=SourceType.JSON_IMPORT,
            title="Textile power module",
            abstract="battery power storage cell textile",
            keywords=["cell", "power"],
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
