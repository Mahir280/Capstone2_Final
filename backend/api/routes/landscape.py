"""Patent landscape endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.schemas import LandscapeResponse
from backend.dependencies import get_landscape_service, get_records
from src.application import LandscapeService
from src.application.dto import LandscapeDTO
from src.application.patent_filters import (
    PatentFilterParams,
    apply_patent_filters,
    ensure_focus_record_included,
    filter_warnings,
)
from src.models.patent import PatentRecord

router = APIRouter(prefix="/api", tags=["landscape"])


def _landscape_filter_params(
    source: list[str] | None = Query(default=None),
    publication_year_from: int | None = Query(default=None),
    publication_year_to: int | None = Query(default=None),
    filing_year_from: int | None = Query(default=None),
    filing_year_to: int | None = Query(default=None),
    country: list[str] | None = Query(default=None),
    assignee: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    application_area: str | None = Query(default=None),
    classification: str | None = Query(default=None),
) -> PatentFilterParams:
    """Parse and validate landscape filter query params."""
    try:
        return PatentFilterParams.from_query(
            source=source,
            publication_year_from=publication_year_from,
            publication_year_to=publication_year_to,
            filing_year_from=filing_year_from,
            filing_year_to=filing_year_to,
            country=country,
            assignee=assignee,
            keyword=keyword,
            application_area=application_area,
            classification=classification,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/landscape", response_model=LandscapeResponse)
def landscape(
    relationship_threshold: float = Query(default=0.20, ge=0.0, le=1.0),
    top_k: int = Query(default=5, ge=1, le=50),
    # Default of 7 follows the GA validation evidence on the canonical corpus
    # (Method & Validation recommends 6 groups; keep in sync with
    # frontend/src/components/landscape/mapGraphPresets.ts).
    technology_group_count: int = Query(default=7, ge=2, le=20),
    max_edges: int = Query(default=80, ge=1, le=2000),
    min_application_score: float = Query(default=0.0, ge=0.0, le=100.0),
    filters: PatentFilterParams = Depends(_landscape_filter_params),
    records: list[PatentRecord] = Depends(get_records),
    landscape_service: LandscapeService = Depends(get_landscape_service),
) -> LandscapeResponse:
    """Return a JSON-ready patent landscape graph."""
    filtered_records = apply_patent_filters(records, filters)
    landscape_dto = landscape_service.build_landscape(
        filtered_records,
        relationship_threshold=relationship_threshold,
        top_k=top_k,
        technology_group_count=technology_group_count,
        max_edges=max_edges,
        min_application_score=min_application_score,
    )
    return _landscape_response(
        landscape_dto,
        records,
        filtered_records,
        filters,
        extra_warnings=filter_warnings(filters, len(filtered_records)),
    )


@router.get(
    "/landscape/focused/{analysis_id:path}",
    response_model=LandscapeResponse,
)
def focused_landscape(
    analysis_id: str,
    relationship_threshold: float = Query(default=0.20, ge=0.0, le=1.0),
    top_k: int = Query(default=5, ge=1, le=50),
    # Default of 7 follows the GA validation evidence on the canonical corpus
    # (Method & Validation recommends 6 groups; keep in sync with
    # frontend/src/components/landscape/mapGraphPresets.ts).
    technology_group_count: int = Query(default=7, ge=2, le=20),
    max_edges: int = Query(default=80, ge=1, le=2000),
    min_application_score: float = Query(default=0.0, ge=0.0, le=100.0),
    filters: PatentFilterParams = Depends(_landscape_filter_params),
    records: list[PatentRecord] = Depends(get_records),
    landscape_service: LandscapeService = Depends(get_landscape_service),
) -> LandscapeResponse:
    """Return a focused patent landscape view around the given analysis id."""
    strict_filtered_records = apply_patent_filters(records, filters)
    filtered_records, focus_record_added = ensure_focus_record_included(
        records,
        strict_filtered_records,
        analysis_id,
    )
    landscape_dto = landscape_service.build_landscape(
        filtered_records,
        selected_analysis_id=analysis_id,
        focused=True,
        relationship_threshold=relationship_threshold,
        top_k=top_k,
        technology_group_count=technology_group_count,
        max_edges=max_edges,
        min_application_score=min_application_score,
    )
    return _landscape_response(
        landscape_dto,
        records,
        filtered_records,
        filters,
        extra_warnings=filter_warnings(
            filters,
            len(strict_filtered_records),
            focus_record_added=focus_record_added,
        ),
    )


def _landscape_response(
    landscape_dto: LandscapeDTO,
    records: list[PatentRecord],
    filtered_records: list[PatentRecord],
    filters: PatentFilterParams,
    *,
    extra_warnings: list[str],
) -> LandscapeResponse:
    """Attach filter metadata to a landscape DTO response."""
    payload = asdict(landscape_dto)
    payload["total_records_before_filter"] = len(records)
    payload["total_records_after_filter"] = len(filtered_records)
    payload["active_filters"] = filters.active_filters()
    payload["warnings"] = _dedupe([*payload.get("warnings", []), *extra_warnings])
    return LandscapeResponse.model_validate(payload)


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
