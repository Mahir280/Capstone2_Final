"""Tests for similarity-based overlap-risk indication."""

from src.clustering.similarity_mapper import (
    PatentSimilarityEdge,
    PatentSimilarityResult,
)
from src.insights import OverlapRiskService
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_service_returns_safe_empty_result_when_no_similarity_edges_exist() -> None:
    records = [_record("US-FIBER-1"), _record("US-FIBER-2")]
    result = OverlapRiskService().evaluate(records, _similarity_result([], records))

    assert result.signals == []
    assert result.signal_count == 0
    assert result.level_counts == {"High": 0, "Medium": 0, "Low": 0, "Minimal": 0}
    assert any("No similarity relationships" in warning for warning in result.warnings)


def test_service_uses_analysis_id_not_patent_id_alone() -> None:
    records = [
        _record("DUPLICATE-1", source=SourceType.CSV_IMPORT),
        _record("DUPLICATE-1", source=SourceType.JSON_IMPORT),
    ]
    result = OverlapRiskService().evaluate(
        records,
        _similarity_result([_edge(records[0], records[1], 0.8)], records),
    )

    signal = result.signals[0]

    assert {
        signal.source_analysis_id,
        signal.target_analysis_id,
    } == {"CSV_IMPORT:DUPLICATE-1", "JSON_IMPORT:DUPLICATE-1"}
    assert signal.source_patent_id == "DUPLICATE-1"
    assert signal.target_patent_id == "DUPLICATE-1"


def test_duplicate_patent_ids_from_different_sources_do_not_collapse() -> None:
    records = [
        _record("DUPLICATE-1", source=SourceType.CSV_IMPORT, title="CSV fiber"),
        _record("DUPLICATE-1", source=SourceType.JSON_IMPORT, title="JSON fiber"),
        _record("UNIQUE-1", source=SourceType.CSV_IMPORT),
    ]
    result = OverlapRiskService().evaluate(
        records,
        _similarity_result(
            [
                _edge(records[0], records[2], 0.7),
                _edge(records[1], records[2], 0.6),
            ],
            records,
        ),
    )

    assert result.signal_count == 2
    assert {signal.source_analysis_id for signal in result.signals} == {
        "CSV_IMPORT:DUPLICATE-1",
        "JSON_IMPORT:DUPLICATE-1",
    }
    assert {signal.source_title for signal in result.signals} == {
        "CSV fiber",
        "JSON fiber",
    }


def test_higher_tfidf_similarity_creates_higher_base_score() -> None:
    records = [_record("A"), _record("B"), _record("C")]
    result = OverlapRiskService().evaluate(
        records,
        _similarity_result(
            [_edge(records[0], records[1], 0.2), _edge(records[0], records[2], 0.8)],
            records,
        ),
    )
    scores_by_target = {
        signal.target_analysis_id: signal.risk_score for signal in result.signals
    }

    assert (
        scores_by_target[records[2].analysis_id]
        > scores_by_target[records[1].analysis_id]
    )
    assert scores_by_target[records[1].analysis_id] == 14.0
    assert scores_by_target[records[2].analysis_id] == 56.0


def test_shared_cluster_increases_risk_score() -> None:
    records = [_record("A"), _record("B")]
    similarity_result = _similarity_result(
        [_edge(records[0], records[1], 0.5)], records
    )

    different_cluster_result = OverlapRiskService().evaluate(
        records,
        similarity_result,
        {records[0].analysis_id: 0, records[1].analysis_id: 1},
    )
    shared_cluster_result = OverlapRiskService().evaluate(
        records,
        similarity_result,
        {records[0].analysis_id: 0, records[1].analysis_id: 0},
    )

    assert shared_cluster_result.signals[0].shared_cluster is True
    assert shared_cluster_result.signals[0].risk_score > (
        different_cluster_result.signals[0].risk_score
    )


def test_shared_keywords_are_included_in_signal_and_explanation() -> None:
    records = [
        _record(
            "A",
            keywords=["Textile Electrode", "biosignal", "fiber"],
        ),
        _record(
            "B",
            keywords=["textile electrode", "BIOSIGNAL", "battery"],
        ),
    ]
    result = OverlapRiskService().evaluate(
        records,
        _similarity_result([_edge(records[0], records[1], 0.3)], records),
    )

    signal = result.signals[0]

    assert signal.shared_keywords == ["biosignal", "textile electrode"]
    assert "shared keywords: biosignal, textile electrode" in signal.explanation


def test_risk_levels_are_assigned_deterministically() -> None:
    records = [_record("A"), _record("B"), _record("C"), _record("D"), _record("E")]
    result = OverlapRiskService().evaluate(
        records,
        _similarity_result(
            [
                _edge(records[0], records[1], 0.1),
                _edge(records[0], records[2], 0.4),
                _edge(records[0], records[3], 0.72),
                _edge(records[0], records[4], 0.9),
            ],
            records,
        ),
        {
            records[0].analysis_id: 0,
            records[1].analysis_id: 1,
            records[2].analysis_id: 2,
            records[3].analysis_id: 3,
            records[4].analysis_id: 0,
        },
    )
    levels_by_target = {
        signal.target_analysis_id: signal.risk_level for signal in result.signals
    }

    assert levels_by_target[records[1].analysis_id] == "Minimal"
    assert levels_by_target[records[2].analysis_id] == "Low"
    assert levels_by_target[records[3].analysis_id] == "Medium"
    assert levels_by_target[records[4].analysis_id] == "High"


def test_result_signals_are_sorted_by_descending_risk_score() -> None:
    records = [_record("A"), _record("B"), _record("C"), _record("D")]
    result = OverlapRiskService().evaluate(
        records,
        _similarity_result(
            [
                _edge(records[0], records[1], 0.3),
                _edge(records[0], records[2], 0.9),
                _edge(records[0], records[3], 0.6),
            ],
            records,
        ),
    )

    assert [signal.risk_score for signal in result.signals] == [
        63.0,
        42.0,
        21.0,
    ]


def test_forbidden_legal_words_do_not_appear_in_generated_strings() -> None:
    records = [
        _record("A", keywords=["fiber", "sensor"]),
        _record("B", keywords=["fiber", "sensor"]),
    ]
    result = OverlapRiskService().evaluate(
        records,
        _similarity_result([_edge(records[0], records[1], 0.85)], records),
        {records[0].analysis_id: 0, records[1].analysis_id: 0},
    )
    forbidden_terms = [
        "infringement",
        "legal violation",
        "copied patent",
        "illegal conflict",
        "legal judgment",
        "legal certainty",
    ]

    generated_text = " ".join(
        f"{signal.risk_level} {signal.explanation}" for signal in result.signals
    ).lower()

    assert not any(term in generated_text for term in forbidden_terms)


def _similarity_result(
    edges: list[PatentSimilarityEdge],
    records: list[PatentRecord],
) -> PatentSimilarityResult:
    return PatentSimilarityResult(
        edges=edges,
        patents_analyzed=len(records),
        threshold=0.0,
        top_k=10,
    )


def _edge(
    source_record: PatentRecord,
    target_record: PatentRecord,
    similarity_score: float,
) -> PatentSimilarityEdge:
    return PatentSimilarityEdge(
        source_analysis_id=source_record.analysis_id,
        target_analysis_id=target_record.analysis_id,
        similarity_score=similarity_score,
        source_patent_id=source_record.patent_id,
        target_patent_id=target_record.patent_id,
        source_title=source_record.title,
        target_title=target_record.title,
    )


def _record(
    patent_id: str,
    *,
    source: SourceType = SourceType.CSV_IMPORT,
    title: str | None = None,
    keywords: list[str] | None = None,
) -> PatentRecord:
    return PatentRecord(
        patent_id=patent_id,
        source=source,
        title=title or f"Patent {patent_id}",
        abstract="Fiber based wearable electronics.",
        keywords=keywords or [],
    )
