"""Pydantic models for the Advanced AI (Genetic Algorithm) endpoint."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdvancedAIRequest(BaseModel):
    """Optional Genetic Algorithm configuration body for /api/advanced-ai/run."""

    model_config = ConfigDict(extra="forbid")

    baseline_cluster_count: int = Field(default=3, ge=2, le=20)
    population_size: int = Field(default=8, ge=2, le=50)
    generations: int = Field(default=5, ge=1, le=50)
    mutation_rate: float = Field(default=0.2, ge=0.0, le=1.0)
    random_state: int = Field(default=42, ge=0)


class AdvancedAIResultResponse(BaseModel):
    """Structured GA optimization result."""

    model_config = ConfigDict(extra="ignore")

    runnable: bool
    status_message: str
    settings: dict[str, float] = Field(default_factory=dict)
    baseline_score: float | None = None
    best_score: float | None = None
    improvement_over_baseline: float | None = None
    best_config: dict[str, Any] | None = None
    generation_history: list[dict[str, Any]] = Field(default_factory=list)
    optimized_assignments: dict[str, int] = Field(default_factory=dict)
    optimized_cluster_sizes: dict[str, int] = Field(default_factory=dict)
    optimized_top_terms_per_cluster: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
