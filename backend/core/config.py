"""Backend runtime configuration."""

from dataclasses import dataclass, field
from pathlib import Path

from src.config.settings import AppSettings


def _default_frontend_dist_dir() -> Path | None:
    """Auto-detect the built React frontend at <repo>/frontend/dist.

    Returns None when no built frontend is present, so the backend continues
    to start cleanly in API-only setups (CI, backend dev, fresh clones).
    """
    # backend/core/config.py → repo root is three parents up.
    repo_root = Path(__file__).resolve().parent.parent.parent
    candidate = repo_root / "frontend" / "dist"
    return candidate if candidate.is_dir() else None


@dataclass(slots=True)
class BackendConfig:
    """Backend-specific runtime configuration."""

    api_title: str = "Fiber Based Wearable Electronics Patent Mapping API"
    api_description: str = (
        "Decision-support API exposing curated source-labeled patent search, "
        "patent profiles, technology landscape, dataset insights, Advanced AI "
        "(Genetic Algorithm) optimization, and local data-source workflows."
    )
    api_version: str = "0.1.0"
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    app_settings: AppSettings = field(default_factory=AppSettings)
    frontend_dist_dir: Path | None = field(default_factory=_default_frontend_dist_dir)


def get_backend_config() -> BackendConfig:
    """Return the backend configuration singleton."""
    return _BACKEND_CONFIG


_BACKEND_CONFIG = BackendConfig()
