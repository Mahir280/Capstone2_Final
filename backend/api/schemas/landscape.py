"""Pydantic models for landscape endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LandscapeNodeModel(BaseModel):
    """One patent node in the landscape graph."""

    model_config = ConfigDict(extra="ignore")

    analysis_id: str
    patent_id: str
    source: str
    source_authority: str
    title: str
    assignee: str | None = None
    country: str | None = None
    technology_group_id: int | None = None
    technology_group: str
    degree: int
    x: float
    y: float
    candidate_application_areas: list[str] = Field(default_factory=list)
    selected: bool = False


class LandscapeEdgeModel(BaseModel):
    """One relationship edge between two patents."""

    model_config = ConfigDict(extra="ignore")

    source_analysis_id: str
    target_analysis_id: str
    relationship_strength: str
    similarity_score: float


class LandscapeResponse(BaseModel):
    """Serialized patent landscape graph."""

    model_config = ConfigDict(extra="ignore")

    nodes: list[LandscapeNodeModel] = Field(default_factory=list)
    edges: list[LandscapeEdgeModel] = Field(default_factory=list)
    node_count: int
    edge_count: int
    technology_group_count: int
    average_relationships: float
    selected_analysis_id: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    technology_groups: list[dict[str, Any]] = Field(default_factory=list)
    technology_group_assignments: dict[str, int] = Field(default_factory=dict)
    grouping_quality_score: float | None = None
    warnings: list[str] = Field(default_factory=list)
    total_records_before_filter: int | None = None
    total_records_after_filter: int | None = None
    active_filters: dict[str, Any] = Field(default_factory=dict)
