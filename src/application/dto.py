"""JSON-serializable application DTOs for future API boundaries."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PatentCardDTO:
    """Compact patent record for search results and selectable lists."""

    analysis_id: str
    patent_id: str
    source: str
    source_authority: str
    import_method: str
    title: str
    abstract_preview: str
    assignee: str | None
    country: str | None
    year: str | None
    keywords: list[str] = field(default_factory=list)
    candidate_application_areas: list[str] = field(default_factory=list)
    match_label: str = "Curated record"
    match_score: int = 0
    source_url: str | None = None


@dataclass(frozen=True, slots=True)
class PatentSearchResponseDTO:
    """Search response suitable for FastAPI JSON serialization later."""

    query: str
    total_results: int
    returned_results: int
    filters: dict[str, str]
    patents: list[PatentCardDTO] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RelatedPatentDTO:
    """Related-patent signal without raw model objects."""

    analysis_id: str
    patent_id: str
    source: str
    source_authority: str
    title: str
    assignee: str | None
    country: str | None
    year: str | None
    relationship_strength: str
    similarity_score: float
    overlap_signal: str
    overlap_score: float
    same_technology_group: bool
    source_technology_group_id: int | None
    target_technology_group_id: int | None
    source_technology_group: str
    target_technology_group: str
    shared_keywords: list[str] = field(default_factory=list)
    candidate_application_areas: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class PatentProfileDTO:
    """Full patent profile response assembled by application services."""

    analysis_id: str
    patent_id: str
    source: str
    source_authority: str
    import_method: str
    title: str
    abstract: str
    plain_language_summary: str
    assignee: str | None
    inventors: list[str]
    publication_date: str | None
    filing_date: str | None
    year: str | None
    country: str | None
    language: str | None
    source_url: str | None
    keywords: list[str]
    ipc_codes: list[str]
    cpc_codes: list[str]
    claims_preview: str | None = None
    top_terms: list[dict[str, Any]] = field(default_factory=list)
    candidate_application_areas: list[dict[str, Any]] = field(default_factory=list)
    related_patents: list[RelatedPatentDTO] = field(default_factory=list)
    metadata_rows: list[dict[str, str]] = field(default_factory=list)
    advanced_metadata_rows: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class LandscapeNodeDTO:
    """One patent node in a JSON-ready landscape graph."""

    analysis_id: str
    patent_id: str
    source: str
    source_authority: str
    title: str
    assignee: str | None
    country: str | None
    technology_group_id: int | None
    technology_group: str
    degree: int
    x: float
    y: float
    candidate_application_areas: list[str] = field(default_factory=list)
    selected: bool = False


@dataclass(frozen=True, slots=True)
class LandscapeEdgeDTO:
    """One JSON-ready relationship edge in a patent landscape."""

    source_analysis_id: str
    target_analysis_id: str
    relationship_strength: str
    similarity_score: float


@dataclass(frozen=True, slots=True)
class LandscapeDTO:
    """JSON-ready patent landscape graph and technology-group summary."""

    nodes: list[LandscapeNodeDTO]
    edges: list[LandscapeEdgeDTO]
    node_count: int
    edge_count: int
    technology_group_count: int
    average_relationships: float
    selected_analysis_id: str | None
    settings: dict[str, int | float | str | bool | None]
    technology_groups: list[dict[str, Any]] = field(default_factory=list)
    technology_group_assignments: dict[str, int] = field(default_factory=dict)
    grouping_quality_score: float | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DatasetInsightsDTO:
    """Dataset-level metrics with only JSON-serializable values."""

    total_patents: int
    source_counts: dict[str, int]
    source_authority_counts: dict[str, int]
    import_method_counts: dict[str, int]
    assignee_counts: dict[str, int]
    year_counts: dict[str, int]
    country_counts: dict[str, int]
    top_keywords: dict[str, int]
    missing_metadata_counts: dict[str, int]
    cluster_distribution: dict[str, int]
    known_organization_count: int
    year_range: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AdvancedAIResultDTO:
    """Structured GA result without optimizer internals."""

    runnable: bool
    status_message: str
    settings: dict[str, int | float]
    baseline_score: float | None = None
    best_score: float | None = None
    improvement_over_baseline: float | None = None
    best_config: dict[str, int | str | None] | None = None
    generation_history: list[dict[str, int | float | None]] = field(
        default_factory=list
    )
    optimized_assignments: dict[str, int] = field(default_factory=dict)
    optimized_cluster_sizes: dict[str, int] = field(default_factory=dict)
    optimized_top_terms_per_cluster: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DataSourceStatusDTO:
    """Status response for local curated datasets and runtime storage."""

    has_patents: bool
    total_patents: int
    database_path: str
    database_exists: bool
    prepared_dataset_path: str
    prepared_dataset_available: bool
    sample_dataset_path: str
    sample_dataset_available: bool
    source_authority_counts: dict[str, int]
    import_method_counts: dict[str, int]
    source_counts: dict[str, int]
    assignee_count: int
    year_range: str
    processed_runtime_files: list[str] = field(default_factory=list)
    status_message: str = ""
    warnings: list[str] = field(default_factory=list)
