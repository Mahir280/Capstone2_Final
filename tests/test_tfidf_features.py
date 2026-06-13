"""Tests for the TF-IDF baseline feature extraction service."""

from src.features.tfidf import TfidfFeatureService, build_combined_analysis_text
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_combined_analysis_text_uses_title_abstract_and_keywords() -> None:
    record = PatentRecord(
        patent_id="US-TEXT-1",
        source=SourceType.CSV_IMPORT,
        title="  Fiber sensor garment  ",
        abstract=" Wearable textile electronics for sensing strain. ",
        claims_text="Claims are intentionally ignored for this baseline.",
        description_text="Descriptions are intentionally ignored for this baseline.",
        keywords=["fiber", " wearable ", "", "sensor"],
    )

    assert build_combined_analysis_text(record) == (
        "Fiber sensor garment\n\n"
        "Wearable textile electronics for sensing strain.\n\n"
        "fiber wearable sensor"
    )


def test_tfidf_can_be_built_from_patent_records() -> None:
    service = TfidfFeatureService()
    records = _sample_records()

    result = service.build_from_patents(records)

    assert result.is_valid
    assert result.analysis_ids == ["CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-BATTERY-1"]
    assert result.patent_ids == ["US-FIBER-1", "US-BATTERY-1"]
    assert result.matrix is not None
    assert result.matrix_shape[0] == 2
    assert result.matrix_shape[1] == result.vocabulary_size
    assert "fiber" in result.feature_names
    assert "battery" in result.feature_names


def test_tfidf_excludes_english_stopwords_from_vocabulary() -> None:
    service = TfidfFeatureService()
    records = [
        PatentRecord(
            patent_id="US-STOPWORD-1",
            source=SourceType.CSV_IMPORT,
            title="The garment of the future",
            abstract="A method for the sensing of strain in the fabric and the yarn.",
            keywords=[],
        ),
        PatentRecord(
            patent_id="US-STOPWORD-2",
            source=SourceType.CSV_IMPORT,
            title="Battery storage textile",
            abstract="The battery and the cell for storage.",
            keywords=[],
        ),
    ]

    result = service.build_from_patents(records)

    assert result.is_valid
    for stopword in ("the", "of", "and", "for"):
        assert stopword not in result.feature_names


def test_tfidf_accepts_optional_vectorizer_config() -> None:
    service = TfidfFeatureService()

    result = service.build_from_patents(
        _sample_records(),
        max_features=3,
        ngram_range=(1, 2),
    )

    assert result.is_valid
    assert result.matrix_shape[0] == 2
    assert result.vocabulary_size <= 3


def test_empty_patent_input_is_handled_safely() -> None:
    service = TfidfFeatureService()

    result = service.build_from_patents([])

    assert not result.is_valid
    assert result.error == "No saved patents are available for TF-IDF analysis."
    assert result.analysis_ids == []
    assert result.patent_ids == []
    assert result.matrix_shape == (0, 0)
    assert result.feature_names == []
    assert result.matrix is None


def test_empty_analysis_text_is_handled_safely() -> None:
    service = TfidfFeatureService()
    records = [
        PatentRecord(
            patent_id="US-EMPTY-1",
            source=SourceType.CSV_IMPORT,
            title=" ",
            abstract="",
            keywords=[],
        )
    ]

    result = service.build_from_patents(records)

    assert not result.is_valid
    assert result.error == (
        "Saved patents do not contain title, abstract, or keywords "
        "for TF-IDF analysis."
    )
    assert result.analysis_ids == ["CSV_IMPORT:US-EMPTY-1"]
    assert result.patent_ids == ["US-EMPTY-1"]
    assert result.matrix_shape == (1, 0)
    assert result.feature_names == []
    assert result.matrix is None


def test_top_terms_for_selected_patent_are_sorted_by_score() -> None:
    service = TfidfFeatureService()
    result = service.build_from_patents(_sample_records())

    terms = service.top_terms_for_patent(result, "CSV_IMPORT:US-FIBER-1", top_n=3)

    assert [term.term for term in terms] == ["fiber", "strain", "garment"]
    assert terms[0].score > terms[1].score


def test_tfidf_preserves_analysis_ids_for_duplicate_patent_ids() -> None:
    service = TfidfFeatureService()
    records = _duplicate_patent_id_records()

    result = service.build_from_patents(records)

    assert result.is_valid
    assert result.patent_ids == ["DUPLICATE-1", "DUPLICATE-1"]
    assert result.analysis_ids == ["CSV_IMPORT:DUPLICATE-1", "JSON_IMPORT:DUPLICATE-1"]
    assert result.matrix_shape[0] == 2


def test_top_terms_lookup_uses_analysis_id_for_duplicate_patent_ids() -> None:
    service = TfidfFeatureService()
    result = service.build_from_patents(_duplicate_patent_id_records())

    csv_terms = service.top_terms_for_patent(result, "CSV_IMPORT:DUPLICATE-1", top_n=2)
    json_terms = service.top_terms_for_patent(
        result, "JSON_IMPORT:DUPLICATE-1", top_n=2
    )

    assert [term.term for term in csv_terms] == ["alpha", "fiber"]
    assert [term.term for term in json_terms] == ["beta", "graphene"]


def _sample_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="US-FIBER-1",
            source=SourceType.CSV_IMPORT,
            title="Fiber sensor garment",
            abstract="fiber fiber strain strain",
            keywords=["textile"],
        ),
        PatentRecord(
            patent_id="US-BATTERY-1",
            source=SourceType.CSV_IMPORT,
            title="Battery storage textile",
            abstract="battery cell storage",
            keywords=["wearable"],
        ),
    ]


def _duplicate_patent_id_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="DUPLICATE-1",
            source=SourceType.CSV_IMPORT,
            title="Alpha fiber textile",
            abstract="alpha alpha fiber",
            keywords=[],
        ),
        PatentRecord(
            patent_id="DUPLICATE-1",
            source=SourceType.JSON_IMPORT,
            title="Beta graphene yarn",
            abstract="beta beta graphene",
            keywords=[],
        ),
    ]
