"""Canonical patent record model."""

from dataclasses import dataclass, field

from src.models.enums import SourceType


@dataclass(slots=True)
class PatentRecord:
    """Normalized patent record used across the analysis pipeline."""

    patent_id: str
    source: SourceType
    title: str
    abstract: str
    publication_number: str | None = None
    claims_text: str | None = None
    claims_excerpt: str | None = None
    description_text: str | None = None
    assignee: str | None = None
    inventors: list[str] = field(default_factory=list)
    publication_date: str | None = None
    filing_date: str | None = None
    ipc_codes: list[str] = field(default_factory=list)
    cpc_codes: list[str] = field(default_factory=list)
    country: str | None = None
    language: str | None = None
    source_url: str | None = None
    keywords: list[str] = field(default_factory=list)
    candidate_application_areas: list[str] = field(default_factory=list)
    patent_family: str | None = None
    citation_count: int | None = None
    raw_source_ref: str | None = None

    @property
    def analysis_id(self) -> str:
        """Return the stable row identifier used by analysis services."""
        return f"{self.source.value}:{self.patent_id}"

    @property
    def combined_text(self) -> str:
        """Return the main textual fields as one clean string."""
        parts = [self.title, self.abstract, self.claims_text, self.description_text]
        return "\n\n".join(part.strip() for part in parts if part and part.strip())
