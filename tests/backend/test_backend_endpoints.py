"""Integration tests for the FastAPI backend endpoints."""

from __future__ import annotations

import subprocess
import sys
from urllib.parse import quote

from fastapi.testclient import TestClient

from backend.dependencies import get_records
from backend.main import create_app
from src.acquisition.file_importer import FileImporter
from src.preprocessing.normalizer import PatentNormalizer
from src.utils.paths import data_path


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app_name"]
    assert payload["api_version"]


def test_patent_search_endpoint_returns_filtered_results(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/patents/search",
        params={"q": "conductive yarn", "country": "US", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_results"] >= 1
    assert payload["patents"]
    assert payload["patents"][0]["patent_id"] == "US-SENSOR-1"
    assert all(card["country"] == "US" for card in payload["patents"])


def test_list_patents_endpoint_paginates(client: TestClient) -> None:
    response = client.get("/api/patents", params={"limit": 2, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 2
    assert payload["offset"] == 0
    assert payload["returned_results"] == 2
    assert payload["total_results"] == 4
    assert len(payload["patents"]) == 2


def test_patent_profile_endpoint_valid_id(client: TestClient) -> None:
    analysis_id = quote("USPTO:US-SENSOR-1", safe="")
    response = client.get(f"/api/patents/{analysis_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"] == "USPTO:US-SENSOR-1"
    assert payload["patent_id"] == "US-SENSOR-1"
    assert payload["plain_language_summary"]
    assert isinstance(payload["candidate_application_areas"], list)


def test_patent_profile_endpoint_returns_404_for_unknown(
    client: TestClient,
) -> None:
    response = client.get(f"/api/patents/{quote('USPTO:UNKNOWN', safe='')}")

    assert response.status_code == 404


def test_related_patents_endpoint(client: TestClient) -> None:
    analysis_id = quote("USPTO:US-SENSOR-1", safe="")
    response = client.get(
        f"/api/patents/{analysis_id}/related",
        params={
            "relationship_threshold": 0.05,
            "top_k": 2,
            "technology_group_count": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"] == "USPTO:US-SENSOR-1"
    assert "related_patents" in payload
    assert isinstance(payload["related_patents"], list)


def test_filters_endpoint_returns_options(client: TestClient) -> None:
    response = client.get("/api/filters")

    assert response.status_code == 200
    payload = response.json()
    assert "USPTO" in payload["sources"]
    assert payload["source_counts"]["USPTO"] == 2
    assert "Fiber Labs" in payload["assignees"]
    assert payload["top_assignees"]["Fiber Labs"] == 2
    assert "US" in payload["countries"]
    assert payload["country_counts"]["US"] == 2
    assert payload["years"]
    assert payload["publication_year_range"] == {"min": 2020, "max": 2023}
    assert payload["filing_year_range"] == {"min": 2019, "max": 2022}
    assert payload["top_keywords"]["smart garment"] == 2
    assert payload["top_application_areas"]["Smart garments"] == 2
    assert "A61B" in payload["top_classifications"]
    assert payload["technology_groups"]


def test_landscape_endpoint_returns_nodes_edges(client: TestClient) -> None:
    response = client.get(
        "/api/landscape",
        params={
            "relationship_threshold": 0.05,
            "top_k": 2,
            "technology_group_count": 2,
            "max_edges": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_count"] == 4
    assert payload["node_count"] == len(payload["nodes"])
    assert payload["edge_count"] == len(payload["edges"])
    assert payload["total_records_before_filter"] == 4
    assert payload["total_records_after_filter"] == 4
    assert payload["active_filters"] == {}
    assert payload["nodes"]
    assert isinstance(payload["edges"], list)


def test_landscape_endpoint_without_filters_returns_full_canonical_corpus() -> None:
    records = _canonical_patent_records()
    expected_count = _canonical_corpus_row_count()
    app = create_app()
    app.dependency_overrides[get_records] = lambda: list(records)
    try:
        with TestClient(app) as test_client:
            response = test_client.get(
                "/api/landscape",
                params={
                    "relationship_threshold": 0.05,
                    "top_k": 3,
                    "technology_group_count": 3,
                    "max_edges": 80,
                },
            )
    finally:
        app.dependency_overrides.clear()

    # Every raw canonical row must normalize successfully and reach the
    # landscape unfiltered; the expected count is derived from the canonical
    # CSV so this test does not go stale when the corpus grows.
    assert expected_count >= 3
    assert len(records) == expected_count
    assert response.status_code == 200
    payload = response.json()
    assert payload["node_count"] == expected_count
    assert payload["total_records_before_filter"] == expected_count
    assert payload["total_records_after_filter"] == expected_count
    assert payload["active_filters"] == {}


def test_landscape_source_filter_limits_records(client: TestClient) -> None:
    payload = _landscape_payload(client, {"source": "EPO"})

    assert payload["node_count"] == 1
    assert payload["total_records_before_filter"] == 4
    assert payload["total_records_after_filter"] == 1
    assert payload["active_filters"] == {"source": ["EPO"]}
    assert {node["source"] for node in payload["nodes"]} == {"EPO"}


def test_landscape_publication_year_range_filter(client: TestClient) -> None:
    payload = _landscape_payload(
        client,
        {"publication_year_from": 2021, "publication_year_to": 2022},
    )

    assert _patent_ids(payload) == {"US-SENSOR-1", "US-SENSOR-2"}
    assert payload["total_records_after_filter"] == 2


def test_landscape_filing_year_range_filter(client: TestClient) -> None:
    payload = _landscape_payload(client, {"filing_year_from": 2022})

    assert _patent_ids(payload) == {"TR-REHAB-1"}
    assert payload["active_filters"] == {"filing_year_from": 2022}


def test_landscape_country_filter(client: TestClient) -> None:
    payload = _landscape_payload(client, {"country": "TR"})

    assert _patent_ids(payload) == {"TR-REHAB-1"}
    assert payload["active_filters"] == {"country": ["TR"]}


def test_landscape_assignee_filter_is_case_insensitive(
    client: TestClient,
) -> None:
    payload = _landscape_payload(client, {"assignee": "fiber labs"})

    assert _patent_ids(payload) == {"US-SENSOR-1", "US-SENSOR-2"}
    assert payload["total_records_after_filter"] == 2


def test_landscape_keyword_filter_matches_text_fields(client: TestClient) -> None:
    payload = _landscape_payload(client, {"keyword": "energy harvesting"})

    assert _patent_ids(payload) == {"EP-POWER-1"}
    assert payload["active_filters"] == {"keyword": "energy harvesting"}


def test_landscape_application_area_filter(client: TestClient) -> None:
    payload = _landscape_payload(client, {"application_area": "rehab"})

    assert _patent_ids(payload) == {"TR-REHAB-1"}
    assert payload["active_filters"] == {"application_area": "rehab"}


def test_landscape_classification_filter(client: TestClient) -> None:
    payload = _landscape_payload(client, {"classification": "G06F"})

    assert _patent_ids(payload) == {"US-SENSOR-1"}
    assert payload["active_filters"] == {"classification": "G06F"}


def test_landscape_combined_filters(client: TestClient) -> None:
    payload = _landscape_payload(
        client,
        {"source": "USPTO", "keyword": "health", "publication_year_from": 2022},
    )

    assert _patent_ids(payload) == {"US-SENSOR-2"}
    assert payload["active_filters"] == {
        "source": ["USPTO"],
        "publication_year_from": 2022,
        "keyword": "health",
    }


def test_landscape_empty_filter_result_is_safe(client: TestClient) -> None:
    payload = _landscape_payload(client, {"assignee": "No Such Assignee"})

    assert payload["node_count"] == 0
    assert payload["edge_count"] == 0
    assert payload["total_records_after_filter"] == 0
    assert payload["warnings"]


def test_landscape_invalid_source_returns_422(client: TestClient) -> None:
    response = client.get("/api/landscape", params={"source": "WIPO"})

    assert response.status_code == 422
    assert "Invalid source" in response.json()["detail"]


def test_landscape_invalid_year_range_returns_422(client: TestClient) -> None:
    response = client.get(
        "/api/landscape",
        params={"publication_year_from": 2024, "publication_year_to": 2020},
    )

    assert response.status_code == 422
    assert "publication_year_from" in response.json()["detail"]


def test_focused_landscape_endpoint(client: TestClient) -> None:
    analysis_id = quote("USPTO:US-SENSOR-1", safe="")
    response = client.get(
        f"/api/landscape/focused/{analysis_id}",
        params={
            "relationship_threshold": 0.05,
            "top_k": 2,
            "technology_group_count": 2,
            "max_edges": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_analysis_id"] == "USPTO:US-SENSOR-1"
    assert isinstance(payload["nodes"], list)


def test_focused_landscape_includes_focus_when_filters_exclude_it(
    client: TestClient,
) -> None:
    analysis_id = quote("USPTO:US-SENSOR-1", safe="")
    response = client.get(
        f"/api/landscape/focused/{analysis_id}",
        params={
            "source": "EPO",
            "relationship_threshold": 0.05,
            "top_k": 2,
            "technology_group_count": 2,
            "max_edges": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_analysis_id"] == "USPTO:US-SENSOR-1"
    assert payload["total_records_before_filter"] == 4
    assert payload["total_records_after_filter"] == 2
    assert payload["active_filters"] == {"source": ["EPO"]}
    assert "US-SENSOR-1" in _patent_ids(payload)
    assert any("focused patent was added" in warning for warning in payload["warnings"])


def test_insights_endpoint(client: TestClient) -> None:
    response = client.get("/api/insights")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_patents"] == 4
    assert payload["source_authority_counts"]["USPTO"] >= 1
    assert payload["known_organization_count"] >= 1


def test_advanced_ai_endpoint_returns_structured_response(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/advanced-ai/run",
        json={
            "baseline_cluster_count": 2,
            "population_size": 4,
            "generations": 2,
            "mutation_rate": 0.2,
            "random_state": 7,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "runnable" in payload
    assert "status_message" in payload
    assert "settings" in payload
    assert "warnings" in payload


def test_advanced_ai_endpoint_accepts_empty_body(client: TestClient) -> None:
    response = client.post("/api/advanced-ai/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["settings"]["baseline_cluster_count"] == 3


def test_data_sources_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/data-sources/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_patents"] is True
    assert payload["total_patents"] == 4
    assert payload["status_message"]


def test_data_sources_load_sample_recovery_handles_missing_file(
    client: TestClient,
) -> None:
    response = client.post("/api/data-sources/load-demo")

    assert response.status_code in (200, 404)


def test_no_streamlit_import_required_for_backend_startup() -> None:
    """Importing backend.main must not transitively import streamlit."""
    code = (
        "import sys\n"
        "import backend.main  # noqa: F401\n"
        "assert 'streamlit' not in sys.modules, sorted(sys.modules)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"backend.main import pulled in streamlit:\n"
        f"stdout={completed.stdout}\nstderr={completed.stderr}"
    )


def _landscape_payload(client: TestClient, params: dict[str, object]) -> dict:
    request_params = {
        "relationship_threshold": 0.05,
        "top_k": 2,
        "technology_group_count": 2,
        "max_edges": 10,
        **params,
    }
    response = client.get("/api/landscape", params=request_params)

    assert response.status_code == 200
    return response.json()


def _patent_ids(payload: dict) -> set[str]:
    return {node["patent_id"] for node in payload["nodes"]}


def _canonical_patent_records() -> list:
    raw_records = FileImporter().import_file(
        data_path("raw", "fiber_wearable_patents_sources.csv")
    )
    normalizer = PatentNormalizer()
    return [
        normalizer.normalize(raw_record, str(raw_record.get("source", "")).strip())
        for raw_record in raw_records
    ]


def _canonical_corpus_row_count() -> int:
    raw_records = FileImporter().import_file(
        data_path("raw", "fiber_wearable_patents_sources.csv")
    )
    return len(raw_records)
