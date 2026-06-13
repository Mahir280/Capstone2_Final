"""Pydantic models for patent search, profile, and filter endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PatentCardModel(BaseModel):
    """Compact patent card for search results and selectable lists."""

    model_config = ConfigDict(extra="ignore")

    analysis_id: str
    patent_id: str
    source: str
    source_authority: str
    import_method: str
    title: str
    abstract_preview: str
    assignee: str | None = None
    country: str | None = None
    year: str | None = None
    keywords: list[str] = Field(default_factory=list)
    candidate_application_areas: list[str] = Field(default_factory=list)
    match_label: str = "Curated record"
    match_score: int = 0
    source_url: str | None = None


class PatentSearchResponse(BaseModel):
    """JSON shape returned by GET /api/patents and /api/patents/search."""

    model_config = ConfigDict(extra="ignore")

    query: str
    total_results: int
    returned_results: int
    filters: dict[str, str]
    patents: list[PatentCardModel] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    limit: int | None = None
    offset: int = 0


class RelatedPatentModel(BaseModel):
    """Related patent overlap signal exposed via API."""

    model_config = ConfigDict(extra="ignore")

    analysis_id: str
    patent_id: str
    source: str
    source_authority: str
    title: str
    assignee: str | None = None
    country: str | None = None
    year: str | None = None
    relationship_strength: str
    similarity_score: float
    overlap_signal: str
    overlap_score: float
    same_technology_group: bool
    source_technology_group_id: int | None = None
    target_technology_group_id: int | None = None
    source_technology_group: str
    target_technology_group: str
    shared_keywords: list[str] = Field(default_factory=list)
    candidate_application_areas: list[str] = Field(default_factory=list)
    explanation: str = ""


class PatentProfileResponse(BaseModel):
    """Full profile for a single patent."""

    model_config = ConfigDict(extra="ignore")

    analysis_id: str
    patent_id: str
    source: str
    source_authority: str
    import_method: str
    title: str
    abstract: str
    plain_language_summary: str
    assignee: str | None = None
    inventors: list[str] = Field(default_factory=list)
    publication_date: str | None = None
    filing_date: str | None = None
    year: str | None = None
    country: str | None = None
    language: str | None = None
    source_url: str | None = None
    keywords: list[str] = Field(default_factory=list)
    ipc_codes: list[str] = Field(default_factory=list)
    cpc_codes: list[str] = Field(default_factory=list)
    claims_preview: str | None = None
    top_terms: list[dict[str, Any]] = Field(default_factory=list)
    candidate_application_areas: list[dict[str, Any]] = Field(default_factory=list)
    related_patents: list[RelatedPatentModel] = Field(default_factory=list)
    metadata_rows: list[dict[str, str]] = Field(default_factory=list)
    advanced_metadata_rows: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RelatedPatentsResponse(BaseModel):
    """Related patents response for /api/patents/{analysis_id}/related."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    related_patents: list[RelatedPatentModel] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FilterOptionsResponse(BaseModel):
    """Available filter options for the patent search UI."""

    model_config = ConfigDict(extra="forbid")

    sources: list[str] = Field(default_factory=list)
    source_counts: dict[str, int] = Field(default_factory=dict)
    assignees: list[str] = Field(default_factory=list)
    top_assignees: dict[str, int] = Field(default_factory=dict)
    countries: list[str] = Field(default_factory=list)
    country_counts: dict[str, int] = Field(default_factory=dict)
    years: list[str] = Field(default_factory=list)
    publication_year_range: dict[str, int | None] = Field(default_factory=dict)
    filing_year_range: dict[str, int | None] = Field(default_factory=dict)
    top_keywords: dict[str, int] = Field(default_factory=dict)
    top_application_areas: dict[str, int] = Field(default_factory=dict)
    classifications: list[str] = Field(default_factory=list)
    top_classifications: dict[str, int] = Field(default_factory=dict)
    technology_groups: list[str] = Field(default_factory=list)
    candidate_application_areas: list[str] = Field(default_factory=list)
