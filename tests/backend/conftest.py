"""Shared fixtures for the FastAPI backend tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.dependencies import (
    get_pipeline_service,
    get_records,
    reset_pipeline_service_cache,
)
from backend.main import create_app
from src.config.settings import AppSettings, StorageConfig
from src.models.enums import SourceType
from src.models.patent import PatentRecord
from src.services.pipeline_service import PipelineService
from src.storage.sqlite_repository import SQLiteRepository


def _backend_test_records() -> list[PatentRecord]:
    """Curated in-memory patent records used by all backend tests."""
    return [
        PatentRecord(
            patent_id="US-SENSOR-1",
            source=SourceType.USPTO,
            title="Conductive yarn pressure sensor garment",
            abstract="A wearable textile pressure sensor using conductive yarn.",
            assignee="Fiber Labs",
            publication_date="2021-05-01",
            filing_date="2020-08-01",
            country="US",
            keywords=["conductive yarn", "pressure sensor", "smart garment"],
            candidate_application_areas=["Smart garments", "Flexible sensors"],
            ipc_codes=["G06F"],
            cpc_codes=["A61B5/00"],
        ),
        PatentRecord(
            patent_id="US-SENSOR-2",
            source=SourceType.USPTO,
            title="Textile electrode health monitoring shirt",
            abstract="A smart garment with textile electrodes for health monitoring.",
            assignee="Fiber Labs",
            publication_date="2022-03-01",
            filing_date="2021-10-15",
            country="US",
            keywords=["textile electrode", "health monitoring", "smart garment"],
            candidate_application_areas=[
                "Healthcare monitoring",
                "Smart garments",
                "Textile electrodes",
            ],
            ipc_codes=["A61B"],
            cpc_codes=["D04B1/00"],
        ),
        PatentRecord(
            patent_id="EP-POWER-1",
            source=SourceType.EPO,
            title="Energy harvesting textile fiber",
            abstract="A self-powered wearable textile with energy harvesting fibers.",
            assignee="Power Weave",
            publication_date="2020-01-01",
            filing_date="2019-06-01",
            country="EP",
            keywords=["energy harvesting", "fiber", "wearable textile"],
            candidate_application_areas=["Energy harvesting textiles"],
            ipc_codes=["H02J"],
            cpc_codes=["D03D"],
        ),
        PatentRecord(
            patent_id="TR-REHAB-1",
            source=SourceType.TURKPATENT,
            title="Rehabilitation movement tracking fabric",
            abstract="A flexible sensor garment for movement tracking therapy.",
            assignee="Rehab Textiles",
            publication_date="2023-07-10",
            filing_date="2022-04-11",
            country="TR",
            keywords=["rehabilitation", "flexible sensor", "movement tracking"],
            candidate_application_areas=["Rehabilitation", "Flexible sensors"],
            ipc_codes=["A61H"],
            cpc_codes=["A61B5/11"],
        ),
    ]


@pytest.fixture()
def patent_records() -> list[PatentRecord]:
    """Return the curated test records."""
    return _backend_test_records()


@pytest.fixture()
def isolated_pipeline_service(tmp_path) -> PipelineService:
    """Build a pipeline service backed by an isolated SQLite database."""
    settings = AppSettings(
        storage=StorageConfig(
            database_path=tmp_path / "patents.sqlite3",
            raw_data_dir=tmp_path / "raw",
            processed_data_dir=tmp_path / "processed",
            exports_dir=tmp_path / "exports",
        )
    )
    settings.storage.raw_data_dir.mkdir(parents=True, exist_ok=True)
    settings.storage.processed_data_dir.mkdir(parents=True, exist_ok=True)
    settings.storage.exports_dir.mkdir(parents=True, exist_ok=True)
    repository = SQLiteRepository(settings.storage.database_path)
    repository.initialize()
    service = PipelineService(settings=settings, repository=repository)
    return service


@pytest.fixture()
def client(
    patent_records: list[PatentRecord],
    isolated_pipeline_service: PipelineService,
) -> Iterator[TestClient]:
    """Return a TestClient with overridden dependencies and curated records."""
    reset_pipeline_service_cache()
    app = create_app()
    app.dependency_overrides[get_records] = lambda: list(patent_records)
    app.dependency_overrides[get_pipeline_service] = lambda: isolated_pipeline_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    reset_pipeline_service_cache()
