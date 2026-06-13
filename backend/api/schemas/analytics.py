"""Pydantic models for the visual analytics endpoint."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CorpusAnalyticsModel(BaseModel):
    """Corpus-composition aggregates."""

    model_config = ConfigDict(extra="ignore")

    by_source: dict[str, int] = Field(default_factory=dict)
    by_country: dict[str, int] = Field(default_factory=dict)
    source_country: dict[str, dict[str, int]] = Field(default_factory=dict)


class TrendAnalyticsModel(BaseModel):
    """Time-trend aggregates keyed by year."""

    model_config = ConfigDict(extra="ignore")

    by_publication_year: dict[str, int] = Field(default_factory=dict)
    by_filing_year: dict[str, int] = Field(default_factory=dict)
    source_by_year: dict[str, dict[str, int]] = Field(default_factory=dict)


class AssigneeAnalyticsModel(BaseModel):
    """Assignee aggregates restricted to the top assignees."""

    model_config = ConfigDict(extra="ignore")

    top: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, dict[str, int]] = Field(default_factory=dict)
    by_application_area: dict[str, dict[str, int]] = Field(default_factory=dict)


class TechnologyAnalyticsModel(BaseModel):
    """Technology aggregates: keywords, application areas, classifications."""

    model_config = ConfigDict(extra="ignore")

    top_keywords: dict[str, int] = Field(default_factory=dict)
    application_areas: dict[str, int] = Field(default_factory=dict)
    classifications: dict[str, int] = Field(default_factory=dict)
    keyword_application_area: dict[str, dict[str, int]] = Field(default_factory=dict)


class QualityAnalyticsModel(BaseModel):
    """Data-quality completeness metrics."""

    model_config = ConfigDict(extra="ignore")

    missing_by_field: dict[str, int] = Field(default_factory=dict)
    field_completeness_pct: dict[str, float] = Field(default_factory=dict)
    completeness_score: float = 0.0


class AnalyticsResponse(BaseModel):
    """Filter-aware visual analytics for the dashboard."""

    model_config = ConfigDict(extra="ignore")

    corpus: CorpusAnalyticsModel = Field(default_factory=CorpusAnalyticsModel)
    trends: TrendAnalyticsModel = Field(default_factory=TrendAnalyticsModel)
    assignees: AssigneeAnalyticsModel = Field(default_factory=AssigneeAnalyticsModel)
    technology: TechnologyAnalyticsModel = Field(
        default_factory=TechnologyAnalyticsModel
    )
    quality: QualityAnalyticsModel = Field(default_factory=QualityAnalyticsModel)
    total_records_before_filter: int = 0
    total_records_after_filter: int = 0
    active_filters: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
