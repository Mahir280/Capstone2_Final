"""Protocol for future patent source adapters."""

from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from src.models.enums import SourceType


class PatentSourceAdapter(Protocol):
    """Contract for future EPO, USPTO, and TURKPATENT source adapters."""

    source_type: SourceType

    def fetch_records(
        self, query: str, limit: int | None = None
    ) -> Iterable[Mapping[str, Any]]:
        """Return raw source records for later normalization."""
        ...
