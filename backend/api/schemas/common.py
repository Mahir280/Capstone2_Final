"""Common response schemas shared across endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Backend liveness response."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok")
    app_name: str
    api_version: str


class MessageResponse(BaseModel):
    """Generic informational response with optional structured details."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok")
    message: str
    details: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
