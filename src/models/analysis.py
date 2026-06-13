"""Models related to analysis run metadata."""

from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisRunMeta:
    """Lightweight metadata for a saved or initialized analysis run."""

    run_id: str
    created_at: str
    source_label: str
    record_count: int
    notes: str | None = None
