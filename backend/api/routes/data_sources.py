"""Local data-source status and loading endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

from backend.api.schemas import DataSourceLoadResponse, DataSourceStatusResponse
from backend.dependencies import (
    get_data_source_service,
    get_pipeline_service,
    get_records,
)
from src.application import DataSourceService
from src.models.patent import PatentRecord
from src.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])


@router.get("/status", response_model=DataSourceStatusResponse)
def status(
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    records: list[PatentRecord] = Depends(get_records),
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceStatusResponse:
    """Return current dataset and runtime storage status."""
    status_dto = data_source_service.get_status(pipeline_service, records)
    return DataSourceStatusResponse.model_validate(asdict(status_dto))


@router.post("/load-prepared", response_model=DataSourceLoadResponse)
def load_prepared(
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceLoadResponse:
    """Load the curated source-labeled dataset into local storage."""
    try:
        summary = data_source_service.load_prepared_source_dataset(pipeline_service)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DataSourceLoadResponse(
        status="ok",
        message="Prepared curated source-labeled dataset loaded.",
        summary=summary,
        warnings=list(summary.get("warnings", [])),
    )


@router.post("/load-demo", response_model=DataSourceLoadResponse)
def load_sample_recovery(
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceLoadResponse:
    """Load the sample/recovery corpus from the canonical local source."""
    try:
        summary = data_source_service.load_sample_recovery_corpus(pipeline_service)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DataSourceLoadResponse(
        status="ok",
        message="Sample/recovery corpus loaded from the canonical corpus.",
        summary=summary,
        warnings=list(summary.get("warnings", [])),
    )
