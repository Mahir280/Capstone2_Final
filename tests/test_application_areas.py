"""Tests for deterministic application-area suggestions."""

from src.insights import ApplicationAreaSuggestionService
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_empty_records_return_safe_empty_results_and_warning() -> None:
    result = ApplicationAreaSuggestionService().analyze([])

    assert result.patent_results == []
    assert result.cluster_results == []
    assert any("No patent records" in warning for warning in result.warnings)


def test_patent_suggestions_detect_healthcare_monitoring_terms() -> None:
    record = _record(
        "HEALTH-1",
        title="Wearable ECG heart rate monitoring shirt",
        abstract="Physiological biosignal monitoring for patient respiration.",
        keywords=["healthcare", "sweat"],
    )

    result = ApplicationAreaSuggestionService().suggest_for_patents([record])[0]
    suggestion = result.suggestions[0]

    assert suggestion.area_name == "Healthcare monitoring"
    assert suggestion.score == 100.0
    assert {"ecg", "heart rate", "monitoring", "healthcare"} <= set(
        suggestion.matched_terms
    )


def test_patent_suggestions_detect_energy_harvesting_textile_terms() -> None:
    record = _record(
        "ENERGY-1",
        title="Self-powered energy harvesting textile",
        abstract="Triboelectric fiber layers support power generation.",
        keywords=["battery-free"],
    )

    result = ApplicationAreaSuggestionService().suggest_for_patents([record])[0]
    suggestion = result.suggestions[0]

    assert suggestion.area_name == "Energy harvesting textiles"
    assert suggestion.score == 100.0
    assert {"self-powered", "energy harvesting", "triboelectric"} <= set(
        suggestion.matched_terms
    )


def test_multiple_suggestions_are_sorted_by_descending_score() -> None:
    record = _record(
        "MULTI-1",
        title="ECG monitoring smart textile",
        abstract="A stretchable flexible sensor for wearable textile monitoring.",
        keywords=["healthcare", "smart textile", "flexible sensor"],
    )

    result = ApplicationAreaSuggestionService().suggest_for_patents([record])[0]
    scores = [suggestion.score for suggestion in result.suggestions]

    assert len(scores) >= 3
    assert scores == sorted(scores, reverse=True)


def test_matched_terms_are_included_and_unique() -> None:
    record = _record(
        "UNIQUE-1",
        title="ECG ECG monitoring textile",
        abstract="ECG monitoring in a wearable textile.",
        keywords=["ecg", "monitoring", "ecg"],
    )

    result = ApplicationAreaSuggestionService().suggest_for_patents([record])[0]
    suggestion = result.suggestions[0]

    assert "ecg" in suggestion.matched_terms
    assert "monitoring" in suggestion.matched_terms
    assert len(suggestion.matched_terms) == len(set(suggestion.matched_terms))
    assert suggestion.evidence_count == len(suggestion.matched_terms)


def test_explanations_mention_evidence_terms_without_overclaiming() -> None:
    record = _record(
        "EXPLAIN-1",
        title="Textile electrode shirt",
        abstract="Conductive fiber supports skin contact signal acquisition.",
        keywords=["textile electrode"],
    )

    result = ApplicationAreaSuggestionService().suggest_for_patents([record])[0]
    explanation = result.suggestions[0].explanation.lower()

    assert "evidence terms" in explanation
    assert "textile electrode" in explanation
    assert "exploratory insight" in explanation


def test_cluster_suggestions_use_analysis_id_assignments() -> None:
    records = [
        _record(
            "DUPLICATE-1",
            source=SourceType.CSV_IMPORT,
            title="CSV unrelated textile",
            abstract="General fabric construction.",
        ),
        _record(
            "DUPLICATE-1",
            source=SourceType.JSON_IMPORT,
            title="JSON ECG monitoring textile",
            abstract="Physiological patient monitoring.",
            keywords=["healthcare"],
        ),
    ]

    result = ApplicationAreaSuggestionService().analyze(
        records,
        cluster_assignments={records[1].analysis_id: 3, "DUPLICATE-1": 9},
    )

    assert len(result.cluster_results) == 1
    cluster_result = result.cluster_results[0]
    assert cluster_result.cluster_id == 3
    assert cluster_result.patent_count == 1
    assert cluster_result.representative_titles == ["JSON ECG monitoring textile"]
    assert cluster_result.suggestions[0].area_name == "Healthcare monitoring"
    assert any("not found" in warning for warning in result.warnings)


def test_duplicate_patent_ids_from_different_sources_do_not_collapse() -> None:
    records = [
        _record(
            "DUPLICATE-1",
            source=SourceType.CSV_IMPORT,
            title="CSV ECG monitoring textile",
            keywords=["healthcare"],
        ),
        _record(
            "DUPLICATE-1",
            source=SourceType.JSON_IMPORT,
            title="JSON energy harvesting textile",
            keywords=["battery-free"],
        ),
    ]

    result = ApplicationAreaSuggestionService().suggest_for_patents(records)

    assert len(result) == 2
    assert {item.analysis_id for item in result} == {
        "CSV_IMPORT:DUPLICATE-1",
        "JSON_IMPORT:DUPLICATE-1",
    }
    assert {item.title for item in result} == {
        "CSV ECG monitoring textile",
        "JSON energy harvesting textile",
    }


def test_unknown_no_match_patent_returns_no_suggestions_and_safe_warning() -> None:
    record = _record(
        "UNKNOWN-1",
        title="Mechanical fastening bracket",
        abstract="A connector assembly for non-wearable equipment.",
        keywords=["fastener"],
    )

    result = ApplicationAreaSuggestionService().suggest_for_patents([record])[0]

    assert result.suggestions == []
    assert any("No application-area evidence" in warning for warning in result.warnings)


def test_forbidden_wording_does_not_appear_in_explanations() -> None:
    records = [
        _record(
            "HEALTH-1",
            title="ECG monitoring shirt",
            abstract="Patient physiological biosignal monitoring.",
            keywords=["healthcare"],
        ),
        _record(
            "ENERGY-1",
            title="Self-powered energy harvesting fabric",
            abstract="Triboelectric textile power generation.",
            keywords=["battery-free"],
        ),
    ]

    results = ApplicationAreaSuggestionService().suggest_for_patents(records)
    generated_text = " ".join(
        suggestion.explanation
        for result in results
        for suggestion in result.suggestions
    ).lower()
    forbidden_terms = [
        "guaranteed",
        "legal",
        "infringement",
        "violation",
        "commercial success",
        "definitive",
    ]

    assert not any(term in generated_text for term in forbidden_terms)


def _record(
    patent_id: str,
    *,
    source: SourceType = SourceType.CSV_IMPORT,
    title: str = "Fiber wearable textile",
    abstract: str = "A fiber based wearable electronics patent.",
    keywords: list[str] | None = None,
) -> PatentRecord:
    return PatentRecord(
        patent_id=patent_id,
        source=source,
        title=title,
        abstract=abstract,
        keywords=keywords or [],
    )
