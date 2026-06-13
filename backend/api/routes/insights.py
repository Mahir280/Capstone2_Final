"""Dataset insight endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, Depends

from backend.api.schemas import DatasetInsightsResponse
from backend.dependencies import get_insights_service, get_records
from src.application import InsightsService
from src.models.patent import PatentRecord

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/insights", response_model=DatasetInsightsResponse)
def insights(
    records: list[PatentRecord] = Depends(get_records),
    insights_service: InsightsService = Depends(get_insights_service),
) -> DatasetInsightsResponse:
    """Return dataset-level metrics and chart-ready data."""
    insights_dto = insights_service.get_insights(records)
    return DatasetInsightsResponse.model_validate(asdict(insights_dto))
