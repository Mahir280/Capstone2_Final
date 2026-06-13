"""Path helpers rooted at the project directory."""

from pathlib import Path


def project_root() -> Path:
    """Return the repository root path."""
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Return the top-level data directory."""
    return project_root() / "data"


def data_path(*parts: str) -> Path:
    """Return a path inside the data directory."""
    return data_dir().joinpath(*parts)
