"""Small dataclass-based settings for the application."""

from dataclasses import dataclass, field
from pathlib import Path

from src.utils.paths import data_path


@dataclass(slots=True)
class StorageConfig:
    """Paths used by the local SQLite-backed storage layer."""

    database_path: Path = field(
        default_factory=lambda: data_path("processed", "patent_analysis.sqlite3")
    )
    raw_data_dir: Path = field(default_factory=lambda: data_path("raw"))
    processed_data_dir: Path = field(default_factory=lambda: data_path("processed"))
    exports_dir: Path = field(default_factory=lambda: data_path("exports"))


@dataclass(slots=True)
class ImportConfig:
    """Basic defaults for future file import behavior."""

    supported_extensions: tuple[str, ...] = (".csv", ".json")
    default_encoding: str = "utf-8"


@dataclass(slots=True)
class PreprocessingConfig:
    """Simple preprocessing defaults for later text cleaning."""

    lowercase: bool = True
    strip_whitespace: bool = True
    default_language: str | None = None


@dataclass(slots=True)
class AppSettings:
    """Application settings grouped by responsibility."""

    app_name: str = "Fiber Based Wearable Electronics Patent Mapping"
    storage: StorageConfig = field(default_factory=StorageConfig)
    imports: ImportConfig = field(default_factory=ImportConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
