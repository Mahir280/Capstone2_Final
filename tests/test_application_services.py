"""Tests for API-ready application services and DTOs."""

import json
from dataclasses import asdict
from types import SimpleNamespace

from src.application import (
    AdvancedAIService,
    DataSourceService,
    InsightsService,
    LandscapeService,
    PatentProfileService,
    PatentSearchService,
)
from src.config.settings import AppSettings
from src.models.enums import SourceType
from src.models.patent import PatentRecord
from src.services.pipeline_service import PipelineService
from src.storage.sqlite_repository import SQLiteRepository


def test_patent_search_service_returns_patent_cards() -> None:
    response = PatentSearchService().search(_service_records(), query="sensor")

    assert response.total_results >= 1
    assert response.patents
    assert response.patents[0].analysis_id
    json.dumps(asdict(response))


def test_patent_search_filtering_and_ranking_work_for_known_query() -> None:
    response = PatentSearchService().search(
        _service_records(),
        query="conductive yarn",
        country_filter="US",
    )

    assert [card.patent_id for card in response.patents][0] == "US-SENSOR-1"
    assert all(card.country == "US" for card in response.patents)


def test_patent_profile_service_returns_profile_for_valid_analysis_id() -> None:
    records = _service_records()
    profile = PatentProfileService().get_profile(records, records[0].analysis_id)

    assert profile is not None
    assert profile.analysis_id == records[0].analysis_id
    assert profile.candidate_application_areas
    json.dumps(asdict(profile))


def test_related_patent_discovery_returns_related_or_safe_empty_result() -> None:
    records = _service_records()
    related_patents, warnings = PatentProfileService().get_related_patents(
        records,
        records[0].analysis_id,
        relationship_threshold=0.05,
        top_k=2,
        technology_group_count=2,
    )

    assert related_patents or warnings
    json.dumps([asdict(related_patent) for related_patent in related_patents])


def test_landscape_service_returns_serializable_nodes_and_edges() -> None:
    landscape = LandscapeService().build_landscape(
        _service_records(),
        relationship_threshold=0.05,
        top_k=2,
        technology_group_count=2,
        max_edges=10,
    )

    assert landscape.nodes
    assert isinstance(landscape.edges, list)
    json.dumps(asdict(landscape))


def test_landscape_group_labels_are_distinct_when_one_area_dominates() -> None:
    service = LandscapeService()
    summaries = [
        SimpleNamespace(cluster_id=0, top_terms=["conductive", "yarn", "sensor"]),
        SimpleNamespace(cluster_id=1, top_terms=["garment", "sensor", "smart"]),
        SimpleNamespace(cluster_id=2, top_terms=["electrode", "textile"]),
    ]
    dominant_area = SimpleNamespace(
        suggestions=[SimpleNamespace(area_name="Energy harvesting textiles")]
    )
    application_by_cluster = {0: dominant_area, 1: dominant_area, 2: dominant_area}

    names = service._distinct_group_names(summaries, application_by_cluster)

    assert len(set(names.values())) == 3
    assert all(name.startswith("Energy harvesting textiles") for name in names.values())
    assert names[0] == "Energy harvesting textiles — conductive yarn focus"


def test_landscape_group_labels_fall_back_to_group_number_without_unique_terms() -> (
    None
):
    service = LandscapeService()
    shared_terms = ["textile", "sensor"]
    summaries = [
        SimpleNamespace(cluster_id=0, top_terms=list(shared_terms)),
        SimpleNamespace(cluster_id=1, top_terms=list(shared_terms)),
    ]
    dominant_area = SimpleNamespace(
        suggestions=[SimpleNamespace(area_name="Smart garments")]
    )
    application_by_cluster = {0: dominant_area, 1: dominant_area}

    names = service._distinct_group_names(summaries, application_by_cluster)

    assert names[0] == "Smart garments — technology group 1"
    assert names[1] == "Smart garments — technology group 2"


def test_insights_service_returns_dataset_level_metrics() -> None:
    insights = InsightsService().get_insights(_service_records())

    assert insights.total_patents == 4
    assert insights.source_authority_counts["USPTO"] >= 1
    assert insights.known_organization_count >= 1
    json.dumps(asdict(insights))


def test_advanced_ai_service_returns_safe_message_when_not_runnable() -> None:
    result = AdvancedAIService().run_optimization(_service_records()[:2])

    assert result.runnable is False
    assert "At least 3" in result.status_message
    json.dumps(asdict(result))


def test_data_source_service_reports_available_prepared_dataset_status(
    tmp_path,
) -> None:
    pipeline_service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )
    status = DataSourceService().get_status(pipeline_service, _service_records())

    assert status.has_patents is True
    assert status.prepared_dataset_available is True
    assert status.sample_dataset_available is True
    assert status.total_patents == 4
    json.dumps(asdict(status))


def _service_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="US-SENSOR-1",
            source=SourceType.USPTO,
            title="Conductive yarn pressure sensor garment",
            abstract="A wearable textile pressure sensor using conductive yarn.",
            assignee="Fiber Labs",
            publication_date="2021-05-01",
            country="US",
            keywords=["conductive yarn", "pressure sensor", "smart garment"],
        ),
        PatentRecord(
            patent_id="US-SENSOR-2",
            source=SourceType.USPTO,
            title="Textile electrode health monitoring shirt",
            abstract="A smart garment with textile electrodes for health monitoring.",
            assignee="Fiber Labs",
            publication_date="2022-03-01",
            country="US",
            keywords=["textile electrode", "health monitoring", "smart garment"],
        ),
        PatentRecord(
            patent_id="EP-POWER-1",
            source=SourceType.EPO,
            title="Energy harvesting textile fiber",
            abstract="A self-powered wearable textile with energy harvesting fibers.",
            assignee="Power Weave",
            publication_date="2020-01-01",
            country="EP",
            keywords=["energy harvesting", "fiber", "wearable textile"],
        ),
        PatentRecord(
            patent_id="TR-REHAB-1",
            source=SourceType.TURKPATENT,
            title="Rehabilitation movement tracking fabric",
            abstract="A flexible sensor garment for movement tracking therapy.",
            assignee="Rehab Textiles",
            publication_date="2023-07-10",
            country="TR",
            keywords=["rehabilitation", "flexible sensor", "movement tracking"],
        ),
    ]
