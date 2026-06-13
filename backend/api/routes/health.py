"""Backend health endpoint."""

from fastapi import APIRouter, Depends

from backend.api.schemas import HealthResponse
from backend.core.config import BackendConfig, get_backend_config

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    config: BackendConfig = Depends(get_backend_config),
) -> HealthResponse:
    """Return basic backend liveness information."""
    return HealthResponse(
        status="ok",
        app_name=config.app_settings.app_name,
        api_version=config.api_version,
    )
