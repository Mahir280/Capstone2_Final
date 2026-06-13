"""Tests for API presentation formatting helpers."""

from src.application._formatting import (
    build_case_canonical_map,
    display_assignee_label,
    format_import_method,
    format_patent_authority,
    grouping_quality_label,
    keyword_importance_label,
    overlap_signal_label,
    relationship_strength_label,
)
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_format_patent_authority_uses_source_labeled_authorities() -> None:
    assert format_patent_authority(_record("EP-1", SourceType.EPO)) == "EPO"
    assert format_patent_authority(_record("US-1", SourceType.USPTO)) == "USPTO"
    assert (
        format_patent_authority(_record("TR-1", SourceType.TURKPATENT))
        == "TURKPATENT/TPO"
    )


def test_format_patent_authority_infers_manual_import_authority_from_id() -> None:
    csv_record = _record("US-2024-001", SourceType.CSV_IMPORT)
    json_record = _record("EP-2024-001", SourceType.JSON_IMPORT)
    turkish_record = _record("TR-2024-001", SourceType.CSV_IMPORT)

    assert format_patent_authority(csv_record) == "USPTO"
    assert format_patent_authority(json_record) == "EPO"
    assert format_patent_authority(turkish_record) == "TURKPATENT/TPO"
    assert csv_record.source is SourceType.CSV_IMPORT


def test_format_patent_authority_handles_unknown_manual_import_prefix() -> None:
    assert (
        format_patent_authority(_record("WO-2024-001", SourceType.CSV_IMPORT))
        == "Unknown authority"
    )


def test_format_import_method_separates_method_from_authority() -> None:
    assert (
        format_import_method(_record("US-2024-001", SourceType.CSV_IMPORT))
        == "CSV file import"
    )
    assert (
        format_import_method(_record("EP-2024-001", SourceType.JSON_IMPORT))
        == "JSON file import"
    )
    assert (
        format_import_method(_record("EP-2024-001", SourceType.EPO))
        == "Source-labeled patent record"
    )


def test_score_helpers_use_plain_language_thresholds() -> None:
    assert relationship_strength_label(0.74) == "Moderate"
    assert relationship_strength_label(0.75) == "Strong"
    assert relationship_strength_label(0.49) == "Light"
    assert relationship_strength_label(0.24) == "Weak"

    assert overlap_signal_label(74.9) == "Medium"
    assert overlap_signal_label(75.0) == "High"
    assert overlap_signal_label(49.9) == "Low"

    assert grouping_quality_label(None) == "Not available"
    assert grouping_quality_label(0.50) == "Strong"
    assert grouping_quality_label(0.25) == "Moderate"
    assert grouping_quality_label(0.24) == "Weak"

    assert keyword_importance_label(0.35) == "Very important"
    assert keyword_importance_label(0.15) == "Important"
    assert keyword_importance_label(0.14) == "Supporting"


def test_display_assignee_label_renames_individual_placeholder() -> None:
    assert display_assignee_label("Individual") == "Individual inventors"
    assert display_assignee_label(" individual ") == "Individual inventors"
    assert display_assignee_label("Individual Corp") == "Individual Corp"
    assert display_assignee_label("Google LLC") == "Google LLC"


def test_build_case_canonical_map_merges_case_variants() -> None:
    mapping = build_case_canonical_map(
        [
            "Smart garments",
            "smart garments",
            "smart garments",
            "Textile sensors",
        ]
    )

    # Most frequent casing wins, then the first letter is capitalized.
    assert mapping["Smart garments"] == "Smart garments"
    assert mapping["smart garments"] == "Smart garments"
    assert mapping["Textile sensors"] == "Textile sensors"


def test_build_case_canonical_map_keeps_distinct_labels_separate() -> None:
    mapping = build_case_canonical_map(["Smart garments", "Smart textiles"])

    assert mapping["Smart garments"] == "Smart garments"
    assert mapping["Smart textiles"] == "Smart textiles"


def _record(patent_id: str, source: SourceType) -> PatentRecord:
    return PatentRecord(
        patent_id=patent_id,
        source=source,
        title="Fiber wearable patent",
        abstract="A fiber-based wearable electronics record.",
    )
