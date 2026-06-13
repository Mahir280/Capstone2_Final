"""Patent search, profile, related-patent, and filter endpoints.

These routes are intentionally thin: they validate query/path inputs,
delegate to ``src.application`` services, and serialize DTOs as JSON.
No TF-IDF, KMeans, similarity, or ranking logic lives here.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.schemas import (
    FilterOptionsResponse,
    PatentProfileResponse,
    PatentSearchResponse,
    RelatedPatentModel,
    RelatedPatentsResponse,
)
from backend.dependencies import (
    get_patent_profile_service,
    get_patent_search_service,
    get_records,
)
from src.application import PatentProfileService, PatentSearchService
from src.application._formatting import technology_group_label
from src.application.patent_filters import build_filter_metadata
from src.models.patent import PatentRecord

router = APIRouter(prefix="/api", tags=["patents"])


@router.get("/patents", response_model=PatentSearchResponse)
def list_patents(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    records: list[PatentRecord] = Depends(get_records),
    search_service: PatentSearchService = Depends(get_patent_search_service),
) -> PatentSearchResponse:
    """Return paginated patent cards from the local curated dataset."""
    return _paginated_search(
        search_service,
        records,
        query="",
        source="All",
        assignee="All",
        country="All",
        year="All",
        limit=limit,
        offset=offset,
    )


@router.get("/patents/search", response_model=PatentSearchResponse)
def search_patents(
    q: str = Query(default="", description="Free-text search query."),
    source: str = Query(default="All", description="Source authority filter."),
    assignee: str = Query(default="All"),
    country: str = Query(default="All"),
    year: str = Query(default="All"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    records: list[PatentRecord] = Depends(get_records),
    search_service: PatentSearchService = Depends(get_patent_search_service),
) -> PatentSearchResponse:
    """Search patents with optional filters and pagination."""
    return _paginated_search(
        search_service,
        records,
        query=q,
        source=source,
        assignee=assignee,
        country=country,
        year=year,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/patents/{analysis_id:path}/related",
    response_model=RelatedPatentsResponse,
)
def related_patents(
    analysis_id: str,
    relationship_threshold: float = Query(default=0.20, ge=0.0, le=1.0),
    top_k: int = Query(default=5, ge=1, le=50),
    # Default of 7 follows the GA validation evidence on the canonical corpus
    # (Method & Validation recommends 6 groups; keep in sync with
    # frontend/src/components/landscape/mapGraphPresets.ts).
    technology_group_count: int = Query(default=7, ge=2, le=20),
    records: list[PatentRecord] = Depends(get_records),
    profile_service: PatentProfileService = Depends(get_patent_profile_service),
) -> RelatedPatentsResponse:
    """Return related patents and overlap signals for a selected patent."""
    related, warnings = profile_service.get_related_patents(
        records,
        analysis_id,
        relationship_threshold=relationship_threshold,
        top_k=top_k,
        technology_group_count=technology_group_count,
    )
    return RelatedPatentsResponse(
        analysis_id=analysis_id,
        related_patents=[
            RelatedPatentModel.model_validate(asdict(item)) for item in related
        ],
        warnings=warnings,
    )


@router.get("/patents/{analysis_id:path}", response_model=PatentProfileResponse)
def patent_profile(
    analysis_id: str,
    include_related: bool = Query(default=True),
    relationship_threshold: float = Query(default=0.20, ge=0.0, le=1.0),
    top_k: int = Query(default=5, ge=1, le=50),
    # Default of 7 follows the GA validation evidence on the canonical corpus
    # (Method & Validation recommends 6 groups; keep in sync with
    # frontend/src/components/landscape/mapGraphPresets.ts).
    technology_group_count: int = Query(default=7, ge=2, le=20),
    records: list[PatentRecord] = Depends(get_records),
    profile_service: PatentProfileService = Depends(get_patent_profile_service),
) -> PatentProfileResponse:
    """Return a full patent profile for the given analysis id."""
    profile = profile_service.get_profile(
        records,
        analysis_id,
        include_related=include_related,
        relationship_threshold=relationship_threshold,
        top_k=top_k,
        technology_group_count=technology_group_count,
    )
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patent analysis id '{analysis_id}' was not found.",
        )
    return PatentProfileResponse.model_validate(asdict(profile))


@router.get("/filters", response_model=FilterOptionsResponse)
def filter_options(
    records: list[PatentRecord] = Depends(get_records),
    search_service: PatentSearchService = Depends(get_patent_search_service),
) -> FilterOptionsResponse:
    """Return available filter values and lightweight counts."""
    metadata = build_filter_metadata(records)
    technology_groups = [technology_group_label(i) for i in range(3)]
    if records and not metadata["candidate_application_areas"]:
        candidate_areas: list[str] = []
        suggestions = search_service.application_area_names(records)
        seen: set[str] = set()
        for area_list in suggestions.values():
            for area in area_list:
                if area not in seen:
                    seen.add(area)
                    candidate_areas.append(area)
        metadata["candidate_application_areas"] = sorted(candidate_areas)

    metadata["technology_groups"] = technology_groups
    return FilterOptionsResponse.model_validate(metadata)


def _paginated_search(
    search_service: PatentSearchService,
    records: list[PatentRecord],
    *,
    query: str,
    source: str,
    assignee: str,
    country: str,
    year: str,
    limit: int,
    offset: int,
) -> PatentSearchResponse:
    response_dto = search_service.search(
        records,
        query=query,
        source_filter=source,
        assignee_filter=assignee,
        country_filter=country,
        year_filter=year,
    )
    sliced = response_dto.patents[offset : offset + limit]
    return PatentSearchResponse.model_validate(
        {
            "query": response_dto.query,
            "total_results": response_dto.total_results,
            "returned_results": len(sliced),
            "filters": response_dto.filters,
            "patents": [asdict(card) for card in sliced],
            "warnings": list(response_dto.warnings),
            "limit": limit,
            "offset": offset,
        }
    )
