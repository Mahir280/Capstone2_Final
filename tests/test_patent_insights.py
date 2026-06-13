"""Tests for basic patent dataset insights."""

from src.insights import PatentInsightsService
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_counts_total_patents_correctly() -> None:
    summary = PatentInsightsService().summarize(_insight_records())

    assert summary.total_patents == 4


def test_counts_sources_correctly() -> None:
    summary = PatentInsightsService().summarize(_insight_records())

    assert summary.source_counts == {"CSV_IMPORT": 3, "JSON_IMPORT": 1}


def test_counts_assignees_correctly() -> None:
    summary = PatentInsightsService().summarize(_insight_records())

    assert summary.assignee_counts["Conductive Textiles Inc"] == 2
    assert summary.assignee_counts["Flexible Power Labs"] == 1


def test_handles_missing_assignee_as_unknown_and_missing() -> None:
    summary = PatentInsightsService().summarize(_insight_records())

    assert summary.assignee_counts["Unknown"] == 1
    assert summary.missing_metadata_counts["assignee"] == 1


def test_extracts_year_trends_from_valid_records() -> None:
    summary = PatentInsightsService().summarize(_insight_records())

    assert summary.year_counts["2020"] == 2
    assert summary.year_counts["2021"] == 1


def test_handles_missing_or_invalid_year_safely() -> None:
    records = [
        _record("BAD-DATE-1", publication_date="not a date"),
        _record("MISSING-DATE-1", publication_date=None, filing_date=None),
    ]

    summary = PatentInsightsService().summarize(records)

    assert summary.year_counts == {"Unknown": 2}
    assert summary.missing_metadata_counts["year"] == 2


def test_counts_countries_when_available() -> None:
    summary = PatentInsightsService().summarize(_insight_records())

    assert summary.country_counts == {"US": 3, "TR": 1}


def test_counts_top_keywords_when_available() -> None:
    summary = PatentInsightsService().summarize(_insight_records())

    assert summary.top_keywords["fiber"] == 3
    assert summary.top_keywords["sensor"] == 2
    assert summary.top_keywords["battery"] == 1


def test_cluster_distribution_uses_analysis_id_assignments() -> None:
    records = _insight_records()
    assignments = {
        records[0].analysis_id: 0,
        records[1].analysis_id: 0,
        records[2].analysis_id: 1,
        "CSV_IMPORT:NOT-IN-DATASET": 9,
    }

    summary = PatentInsightsService().summarize(
        records, cluster_assignments=assignments
    )

    assert summary.cluster_distribution == {0: 2, 1: 1}


def _insight_records() -> list[PatentRecord]:
    return [
        _record(
            "US-FIBER-1",
            source=SourceType.CSV_IMPORT,
            assignee="Conductive Textiles Inc",
            publication_date="2020-05-01",
            country="US",
            keywords=["Fiber", "sensor"],
        ),
        _record(
            "US-FIBER-2",
            source=SourceType.CSV_IMPORT,
            assignee="Conductive Textiles Inc",
            publication_date="2020",
            country="US",
            keywords=["fiber", "wearable"],
        ),
        _record(
            "TR-BATTERY-1",
            source=SourceType.JSON_IMPORT,
            assignee="Flexible Power Labs",
            publication_date="2021/03/15",
            country="TR",
            keywords=["battery", "sensor"],
        ),
        _record(
            "US-UNKNOWN-1",
            source=SourceType.CSV_IMPORT,
            assignee=None,
            publication_date="invalid",
            country="US",
            keywords=["fiber"],
        ),
    ]


def _record(
    patent_id: str,
    *,
    source: SourceType = SourceType.CSV_IMPORT,
    title: str = "Fiber wearable invention",
    abstract: str = "A fiber based wearable electronics patent.",
    assignee: str | None = "Example Assignee",
    publication_date: str | None = "2020-01-01",
    filing_date: str | None = None,
    country: str | None = "US",
    keywords: list[str] | None = None,
) -> PatentRecord:
    return PatentRecord(
        patent_id=patent_id,
        source=source,
        title=title,
        abstract=abstract,
        assignee=assignee,
        publication_date=publication_date,
        filing_date=filing_date,
        country=country,
        keywords=keywords or ["fiber"],
    )
