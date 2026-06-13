"""Pydantic models for local data-source endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DataSourceStatusResponse(BaseModel):
    """Local data-source and runtime storage status."""

    model_config = ConfigDict(extra="ignore")

    has_patents: bool
    total_patents: int
    database_path: str
    database_exists: bool
    prepared_dataset_path: str
    prepared_dataset_available: bool
    sample_dataset_path: str
    sample_dataset_available: bool
    source_authority_counts: dict[str, int] = Field(default_factory=dict)
    import_method_counts: dict[str, int] = Field(default_factory=dict)
    source_counts: dict[str, int] = Field(default_factory=dict)
    assignee_count: int
    year_range: str
    processed_runtime_files: list[str] = Field(default_factory=list)
    status_message: str = ""
    warnings: list[str] = Field(default_factory=list)


class DataSourceLoadResponse(BaseModel):
    """Result of a local dataset load operation."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(default="ok")
    message: str
    summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
