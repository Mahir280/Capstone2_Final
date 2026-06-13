"""Tests for pure patent search application ranking helpers."""

from src.application._formatting import primary_authority_label
from src.application.patent_search_service import PatentSearchService
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_rank_records_prefers_exact_patent_id_match() -> None:
    service = PatentSearchService()
    title_match = _record(
        "US-OTHER",
        title="Wearable sensor for US-42 monitoring",
        abstract="A smart textile patent.",
    )
    exact_id_match = _record(
        "US-42",
        title="Conductive textile electrode",
        abstract="A fiber-based wearable electronics patent.",
    )

    ranked = service.rank_records([title_match, exact_id_match], query="US-42")

    assert ranked[0].record.patent_id == "US-42"
    assert ranked[0].match_label == "Best match"


def test_rank_records_weights_title_and_keywords_above_abstract() -> None:
    service = PatentSearchService()
    abstract_match = _record(
        "US-1",
        title="General wearable system",
        abstract="The garment uses conductive yarn for sensing.",
    )
    keyword_match = _record(
        "US-2",
        title="Fiber electronics assembly",
        abstract="A wearable textile patent.",
        keywords=["conductive yarn"],
    )
    title_match = _record(
        "US-3",
        title="Conductive yarn pressure sensor",
        abstract="A wearable textile patent.",
    )

    ranked = service.rank_records(
        [abstract_match, keyword_match, title_match],
        query="conductive yarn",
    )

    assert [result.record.patent_id for result in ranked] == ["US-3", "US-2", "US-1"]
    assert ranked[0].match_label == "Strong match"


def test_matches_search_accepts_non_contiguous_query_terms() -> None:
    service = PatentSearchService()
    record = _record(
        "EP-1",
        title="Conductive textile architecture",
        abstract="A pressure sensor woven into fabric.",
    )

    assert service.matches_search(record, "conductive architecture")


def test_primary_authority_label_keeps_import_method_out_of_source_label() -> None:
    record = _record(
        "WO-2024-001",
        title="Wearable textile system",
        abstract="A smart garment patent.",
        source=SourceType.CSV_IMPORT,
    )

    assert primary_authority_label(record) == "Unknown"


def _record(
    patent_id: str,
    *,
    title: str,
    abstract: str,
    source: SourceType = SourceType.USPTO,
    keywords: list[str] | None = None,
) -> PatentRecord:
    return PatentRecord(
        patent_id=patent_id,
        source=source,
        title=title,
        abstract=abstract,
        keywords=keywords or [],
    )
