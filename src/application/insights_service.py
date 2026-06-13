"""Application service for dataset-level insight DTOs."""

from src.application._formatting import (
    import_method_counts,
    known_count,
    source_authority_counts,
    year_range_from_counts,
)
from src.application.dto import DatasetInsightsDTO
from src.insights import PatentInsightsService, PatentInsightSummary
from src.models.patent import PatentRecord


class InsightsService:
    """Assemble JSON-ready dataset insight responses."""

    def __init__(
        self,
        *,
        insights_service: PatentInsightsService | None = None,
    ) -> None:
        self.insights_service = insights_service or PatentInsightsService()

    def get_insights(
        self,
        records: list[PatentRecord],
        *,
        summary: PatentInsightSummary | None = None,
        cluster_assignments: dict[str, int] | None = None,
    ) -> DatasetInsightsDTO:
        """Return dataset-level metrics for API or UI consumers."""
        resolved_summary = summary or self.insights_service.summarize(
            records,
            cluster_assignments=cluster_assignments,
        )
        warnings: list[str] = []
        if not records:
            warnings.append("No patent records are available for dataset insights.")

        return DatasetInsightsDTO(
            total_patents=resolved_summary.total_patents,
            source_counts=dict(resolved_summary.source_counts),
            source_authority_counts=source_authority_counts(records),
            import_method_counts=import_method_counts(records),
            assignee_counts=dict(resolved_summary.assignee_counts),
            year_counts=dict(resolved_summary.year_counts),
            country_counts=dict(resolved_summary.country_counts),
            top_keywords=dict(resolved_summary.top_keywords),
            missing_metadata_counts=dict(resolved_summary.missing_metadata_counts),
            cluster_distribution={
                str(cluster_id): count
                for cluster_id, count in resolved_summary.cluster_distribution.items()
            },
            known_organization_count=known_count(resolved_summary.assignee_counts),
            year_range=year_range_from_counts(resolved_summary.year_counts),
            warnings=warnings,
        )
