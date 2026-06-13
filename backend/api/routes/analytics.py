"""Visual analytics endpoint."""

from dataclasses import asdict

from fastapi import APIRouter, Depends

from backend.api.routes.landscape import _landscape_filter_params
from backend.api.schemas import AnalyticsResponse
from backend.dependencies import get_analytics_service, get_records
from src.application import AnalyticsService
from src.application.patent_filters import (
    PatentFilterParams,
    apply_patent_filters,
    filter_warnings,
)
from src.models.patent import PatentRecord

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(
    filters: PatentFilterParams = Depends(_landscape_filter_params),
    records: list[PatentRecord] = Depends(get_records),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsResponse:
    """Return filter-aware visual analytics for the dashboard."""
    filtered_records = apply_patent_filters(records, filters)
    analytics_dto = analytics_service.build_analytics(filtered_records)

    payload = asdict(analytics_dto)
    payload["total_records_before_filter"] = len(records)
    payload["total_records_after_filter"] = len(filtered_records)
    payload["active_filters"] = filters.active_filters()

    warnings = filter_warnings(filters, len(filtered_records))
    if not filtered_records and not filters.has_filters:
        warnings = ["No patent records are available for analytics."]
    payload["warnings"] = warnings

    return AnalyticsResponse.model_validate(payload)
