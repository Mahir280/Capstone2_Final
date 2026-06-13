"""Tests for canonical patent normalization."""

import pytest

from src.models.enums import SourceType
from src.preprocessing.normalizer import PatentNormalizer


def test_normalizer_maps_aliases_and_cleans_list_fields() -> None:
    raw_record = {
        "publication_number": " US-2026-0001 ",
        "title": "  Fiber sensor garment ",
        "summary": " Wearable textile electronics. ",
        "claims_excerpt": " Claim text ",
        "applicant": " Example Labs ",
        "inventor": " Ada Example ; Bob Example ",
        "pub_date": "2026-01-02",
        "ipc": "A61B|G06F",
        "cpc": "A61B 5/00, H01B 7/00",
        "keywords": "fiber; wearable | sensor",
        "candidate_application_areas": "Healthcare monitoring; Smart garments",
        "patent_family": "123456",
        "citation_count": "24",
        "url": " https://example.test/patent ",
    }

    record = PatentNormalizer().normalize(raw_record, SourceType.CSV_IMPORT)

    assert record.patent_id == "US-2026-0001"
    assert record.publication_number == "US-2026-0001"
    assert record.title == "Fiber sensor garment"
    assert record.abstract == "Wearable textile electronics."
    assert record.claims_text == "Claim text"
    assert record.claims_excerpt == "Claim text"
    assert record.assignee == "Example Labs"
    assert record.inventors == ["Ada Example", "Bob Example"]
    assert record.publication_date == "2026-01-02"
    assert record.ipc_codes == ["A61B", "G06F"]
    assert record.cpc_codes == ["A61B 5/00", "H01B 7/00"]
    assert record.keywords == ["fiber", "wearable", "sensor"]
    assert record.candidate_application_areas == [
        "Healthcare monitoring",
        "Smart garments",
    ]
    assert record.patent_family == "123456"
    assert record.citation_count == 24
    assert record.source_url == "https://example.test/patent"
    assert record.source is SourceType.CSV_IMPORT


def test_normalizer_rejects_rows_missing_required_fields() -> None:
    raw_record = {"abstract": "No patent id or title."}

    with pytest.raises(ValueError, match="Missing required field: patent_id"):
        PatentNormalizer().normalize(raw_record, SourceType.JSON_IMPORT)
