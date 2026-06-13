"""Pydantic models for dataset insight endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class DatasetInsightsResponse(BaseModel):
    """Dataset-level metrics and chart-ready data."""

    model_config = ConfigDict(extra="ignore")

    total_patents: int
    source_counts: dict[str, int] = Field(default_factory=dict)
    source_authority_counts: dict[str, int] = Field(default_factory=dict)
    import_method_counts: dict[str, int] = Field(default_factory=dict)
    assignee_counts: dict[str, int] = Field(default_factory=dict)
    year_counts: dict[str, int] = Field(default_factory=dict)
    country_counts: dict[str, int] = Field(default_factory=dict)
    top_keywords: dict[str, int] = Field(default_factory=dict)
    missing_metadata_counts: dict[str, int] = Field(default_factory=dict)
    cluster_distribution: dict[str, int] = Field(default_factory=dict)
    known_organization_count: int
    year_range: str
    warnings: list[str] = Field(default_factory=list)
