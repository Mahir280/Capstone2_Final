"""Application service for local data-source status and loading workflows."""

from pathlib import Path
from typing import Any

from src.application._formatting import (
    import_method_counts,
    known_count,
    source_authority_counts,
    year_range_from_counts,
)
from src.application.dto import DataSourceStatusDTO
from src.insights import PatentInsightsService, PatentInsightSummary
from src.models.patent import PatentRecord
from src.services.pipeline_service import (
    PREPARED_SOURCE_DATASET_FILENAME,
    SAMPLE_RECOVERY_CORPUS_FILENAME,
    PipelineService,
)


class DataSourceService:
    """Report and run local curated dataset workflows."""

    def __init__(
        self,
        *,
        insights_service: PatentInsightsService | None = None,
    ) -> None:
        self.insights_service = insights_service or PatentInsightsService()

    def get_status(
        self,
        pipeline_service: PipelineService,
        records: list[PatentRecord],
        *,
        summary: PatentInsightSummary | None = None,
    ) -> DataSourceStatusDTO:
        """Return local data-source and runtime storage status."""
        resolved_summary = summary or self.insights_service.summarize(records)
        raw_data_dir = Path(pipeline_service.settings.storage.raw_data_dir)
        processed_dir = Path(pipeline_service.settings.storage.processed_data_dir)
        database_path = Path(pipeline_service.repository.database_path)
        prepared_dataset_path = raw_data_dir / PREPARED_SOURCE_DATASET_FILENAME
        sample_dataset_path = raw_data_dir / SAMPLE_RECOVERY_CORPUS_FILENAME
        runtime_files = self._processed_runtime_files(processed_dir)
        warnings: list[str] = []
        if runtime_files:
            warnings.append(
                "Runtime files are present in data/processed; .gitkeep is preserved."
            )

        return DataSourceStatusDTO(
            has_patents=bool(records),
            total_patents=len(records),
            database_path=str(database_path),
            database_exists=database_path.exists(),
            prepared_dataset_path=str(prepared_dataset_path),
            prepared_dataset_available=prepared_dataset_path.exists(),
            sample_dataset_path=str(sample_dataset_path),
            sample_dataset_available=sample_dataset_path.exists(),
            source_authority_counts=source_authority_counts(records),
            import_method_counts=import_method_counts(records),
            source_counts=dict(resolved_summary.source_counts),
            assignee_count=known_count(resolved_summary.assignee_counts),
            year_range=year_range_from_counts(resolved_summary.year_counts),
            processed_runtime_files=runtime_files,
            status_message=self._status_message(records),
            warnings=warnings,
        )

    def load_prepared_source_dataset(
        self,
        pipeline_service: PipelineService,
    ) -> dict[str, Any]:
        """Load the curated source-labeled dataset through the existing pipeline."""
        return pipeline_service.load_prepared_source_dataset()

    def load_demo_dataset(self, pipeline_service: PipelineService) -> dict[str, Any]:
        """Load the sample/recovery corpus through the existing pipeline."""
        return self.load_sample_recovery_corpus(pipeline_service)

    def load_sample_recovery_corpus(
        self,
        pipeline_service: PipelineService,
    ) -> dict[str, Any]:
        """Load the canonical corpus for recovery/testing workflows."""
        return pipeline_service.load_sample_recovery_corpus()

    def import_patents(
        self,
        pipeline_service: PipelineService,
        file_source: object,
        *,
        import_type: str | None = None,
    ) -> dict[str, Any]:
        """Import uploaded or local patent records through the existing pipeline."""
        return pipeline_service.import_patents(file_source, import_type=import_type)

    def _processed_runtime_files(self, processed_dir: Path) -> list[str]:
        if not processed_dir.exists():
            return []
        return sorted(
            path.name
            for path in processed_dir.iterdir()
            if path.is_file() and path.name != ".gitkeep"
        )

    def _status_message(self, records: list[PatentRecord]) -> str:
        if records:
            return (
                "A saved curated source-labeled dataset is available for exploration."
            )
        return (
            "No saved patent records are available yet; load the prepared curated "
            "dataset or import prepared records."
        )
