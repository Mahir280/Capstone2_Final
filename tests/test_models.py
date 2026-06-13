"""Tests for the canonical scaffold models."""

from src.models.analysis import AnalysisRunMeta
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_patent_record_combined_text_uses_available_text_fields() -> None:
    record = PatentRecord(
        patent_id="US-TEST-1",
        source=SourceType.CSV_IMPORT,
        title="Fiber sensor garment",
        abstract="Wearable textile electronics for sensing strain.",
        claims_text="A fiber-based wearable sensor claim.",
        inventors=["Ada Example"],
        ipc_codes=["G06F"],
        cpc_codes=["A61B"],
        keywords=["fiber", "wearable"],
    )

    assert record.combined_text == (
        "Fiber sensor garment\n\n"
        "Wearable textile electronics for sensing strain.\n\n"
        "A fiber-based wearable sensor claim."
    )


def test_patent_record_combined_text_skips_blank_optional_fields() -> None:
    record = PatentRecord(
        patent_id="TR-TEST-1",
        source=SourceType.JSON_IMPORT,
        title="Textile electrode",
        abstract="  Conductive fiber system.  ",
        claims_text="",
        description_text=None,
    )

    assert record.combined_text == "Textile electrode\n\nConductive fiber system."


def test_patent_record_analysis_id_uses_source_and_patent_id() -> None:
    record = PatentRecord(
        patent_id="US-DUPLICATE-1",
        source=SourceType.USPTO,
        title="Fiber electrode",
        abstract="Conductive wearable fiber.",
    )

    assert record.analysis_id == "USPTO:US-DUPLICATE-1"


def test_analysis_run_meta_holds_minimal_run_metadata() -> None:
    run = AnalysisRunMeta(
        run_id="run-001",
        created_at="2026-04-24T00:00:00",
        source_label="csv import",
        record_count=12,
    )

    assert run.notes is None
    assert run.record_count == 12
