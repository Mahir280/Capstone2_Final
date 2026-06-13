"""Tests for the visual analytics endpoint and service."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.application.analytics_service import AnalyticsService
from src.models.enums import SourceType
from src.models.patent import PatentRecord


def test_analytics_endpoint_unfiltered_shape(client: TestClient) -> None:
    response = client.get("/api/analytics")

    assert response.status_code == 200
    payload = response.json()

    assert payload["total_records_before_filter"] == 4
    assert payload["total_records_after_filter"] == 4
    assert payload["active_filters"] == {}
    assert payload["warnings"] == []

    for section in ("corpus", "trends", "assignees", "technology", "quality"):
        assert section in payload

    assert payload["corpus"]["by_source"] == {
        "USPTO": 2,
        "EPO": 1,
        "TURKPATENT/TPO": 1,
    }
    assert payload["corpus"]["by_country"] == {"US": 2, "EP": 1, "TR": 1}
    assert payload["corpus"]["source_country"]["USPTO"] == {"US": 2}


def test_analytics_endpoint_sections_have_expected_data(client: TestClient) -> None:
    payload = client.get("/api/analytics").json()

    trends = payload["trends"]
    assert trends["by_publication_year"]["2021"] == 1
    assert trends["by_filing_year"]["2020"] == 1
    assert "USPTO" in trends["source_by_year"]["2021"]

    assignees = payload["assignees"]
    assert assignees["top"]["Fiber Labs"] == 2
    assert assignees["by_source"]["Fiber Labs"] == {"USPTO": 2}
    assert "Smart garments" in assignees["by_application_area"]["Fiber Labs"]

    technology = payload["technology"]
    assert technology["top_keywords"]["smart garment"] == 2
    assert technology["application_areas"]["Smart garments"] == 2
    assert technology["classifications"]
    assert "smart garment" in technology["keyword_application_area"]


def test_analytics_quality_metrics_complete_corpus(client: TestClient) -> None:
    quality = client.get("/api/analytics").json()["quality"]

    assert set(quality["missing_by_field"]) == {
        "assignee",
        "country",
        "publication_date",
        "filing_date",
        "abstract",
        "keywords",
        "ipc_codes",
        "cpc_codes",
        "application_areas",
    }
    # The curated corpus populates every tracked field on every record.
    assert all(count == 0 for count in quality["missing_by_field"].values())
    assert quality["completeness_score"] == 1.0
    assert quality["field_completeness_pct"]["assignee"] == 100.0


def test_analytics_endpoint_single_source_filter(client: TestClient) -> None:
    response = client.get("/api/analytics", params={"source": "USPTO"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_records_before_filter"] == 4
    assert payload["total_records_after_filter"] == 2
    assert payload["active_filters"] == {"source": ["USPTO"]}
    assert payload["corpus"]["by_source"] == {"USPTO": 2}


def test_analytics_endpoint_keyword_filter(client: TestClient) -> None:
    response = client.get("/api/analytics", params={"keyword": "sensor"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_filters"] == {"keyword": "sensor"}
    # US-SENSOR-1 and TR-REHAB-1 mention "sensor"; the other two do not.
    assert payload["total_records_after_filter"] == 2
    assert set(payload["corpus"]["by_source"]) == {"USPTO", "TURKPATENT/TPO"}


def test_analytics_endpoint_multi_source_filter(client: TestClient) -> None:
    response = client.get(
        "/api/analytics",
        params=[("source", "USPTO"), ("source", "EPO")],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_records_after_filter"] == 3
    assert payload["active_filters"]["source"] == ["USPTO", "EPO"]


def test_analytics_endpoint_rejects_invalid_source(client: TestClient) -> None:
    response = client.get("/api/analytics", params={"source": "NOT-A-SOURCE"})

    assert response.status_code == 422


def test_analytics_endpoint_empty_filter_result_warns(client: TestClient) -> None:
    response = client.get("/api/analytics", params={"assignee": "no-such-company"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_records_after_filter"] == 0
    assert payload["warnings"]


def test_analytics_service_quality_detects_missing_fields() -> None:
    records = [
        PatentRecord(
            patent_id="A-1",
            source=SourceType.USPTO,
            title="Complete record",
            abstract="Has every tracked field populated.",
            assignee="Acme",
            publication_date="2021-01-01",
            filing_date="2020-01-01",
            country="US",
            keywords=["sensor"],
            candidate_application_areas=["Sensing"],
            ipc_codes=["G01S"],
            cpc_codes=["G01S7/00"],
        ),
        PatentRecord(
            patent_id="B-2",
            source=SourceType.EPO,
            title="Sparse record",
            abstract="Missing assignee, filing date, codes, and areas.",
            country="EP",
            keywords=["fiber"],
        ),
    ]

    quality = AnalyticsService().build_analytics(records).quality

    assert quality.missing_by_field["assignee"] == 1
    assert quality.missing_by_field["filing_date"] == 1
    assert quality.missing_by_field["ipc_codes"] == 1
    assert quality.missing_by_field["application_areas"] == 1
    assert quality.missing_by_field["country"] == 0
    assert quality.field_completeness_pct["country"] == 100.0
    assert 0.0 < quality.completeness_score < 1.0


def test_analytics_service_handles_empty_records() -> None:
    dto = AnalyticsService().build_analytics([])

    assert dto.corpus.by_source == {}
    assert dto.trends.by_publication_year == {}
    assert dto.assignees.top == {}
    assert dto.technology.top_keywords == {}
    assert dto.quality.completeness_score == 0.0
    assert all(count == 0 for count in dto.quality.missing_by_field.values())
