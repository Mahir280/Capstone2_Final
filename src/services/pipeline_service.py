"""Thin orchestration for patent dataset imports."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any

from src.acquisition.corpus_quality import (
    CANONICAL_CORPUS_ACCEPTED_REQUIRED_FIELDS,
    CANONICAL_CORPUS_CLASSIFICATION_FIELDS,
    CANONICAL_CORPUS_SCHEMA_COLUMNS,
    CANONICAL_CORPUS_STRONGLY_PREFERRED_FIELDS,
    REVIEW_NEEDED_SCHEMA_COLUMNS,
)
from src.acquisition.file_importer import FileImporter, FileInput
from src.config.settings import AppSettings
from src.models.enums import SourceType
from src.models.patent import PatentRecord
from src.preprocessing.normalizer import PatentNormalizer
from src.storage.sqlite_repository import SQLiteRepository

CANONICAL_CORPUS_FILENAME = "fiber_wearable_patents_sources.csv"
PREPARED_SOURCE_DATASET_FILENAME = CANONICAL_CORPUS_FILENAME
SAMPLE_RECOVERY_CORPUS_FILENAME = CANONICAL_CORPUS_FILENAME
CANONICAL_CORPUS_CRITICAL_FIELDS = CANONICAL_CORPUS_ACCEPTED_REQUIRED_FIELDS
PREPARED_SOURCE_DATASET_REQUIRED_COLUMNS = (
    "patent_id",
    "source",
    "title",
    "abstract",
    "assignee",
    "inventors",
    "publication_date",
    "filing_date",
    "country",
    "keywords",
    "source_url",
)
PREPARED_SOURCE_TYPES = (
    SourceType.EPO,
    SourceType.USPTO,
    SourceType.TURKPATENT,
)
PREPARED_SOURCE_LABEL_ALIASES = {
    "EPO": SourceType.EPO,
    "EUROPEAN_PATENT_OFFICE": SourceType.EPO,
    "USPTO": SourceType.USPTO,
    "US_PATENT_AND_TRADEMARK_OFFICE": SourceType.USPTO,
    "UNITED_STATES_PATENT_AND_TRADEMARK_OFFICE": SourceType.USPTO,
    "TPO": SourceType.TURKPATENT,
    "TURKPATENT": SourceType.TURKPATENT,
    "TURKPATENT_TPO": SourceType.TURKPATENT,
    "TPO_TURKPATENT": SourceType.TURKPATENT,
    "TURK_PATENT": SourceType.TURKPATENT,
    "TURKISH_PATENT_OFFICE": SourceType.TURKPATENT,
}

__all__ = [
    "CANONICAL_CORPUS_ACCEPTED_REQUIRED_FIELDS",
    "CANONICAL_CORPUS_CLASSIFICATION_FIELDS",
    "CANONICAL_CORPUS_CRITICAL_FIELDS",
    "CANONICAL_CORPUS_FILENAME",
    "CANONICAL_CORPUS_SCHEMA_COLUMNS",
    "CANONICAL_CORPUS_STRONGLY_PREFERRED_FIELDS",
    "PREPARED_SOURCE_DATASET_FILENAME",
    "PREPARED_SOURCE_DATASET_REQUIRED_COLUMNS",
    "PREPARED_SOURCE_LABEL_ALIASES",
    "PREPARED_SOURCE_TYPES",
    "PipelineService",
    "REVIEW_NEEDED_SCHEMA_COLUMNS",
    "SAMPLE_RECOVERY_CORPUS_FILENAME",
]


@dataclass(slots=True)
class PipelineService:
    """Coordinate import, normalization, and storage without UI logic."""

    settings: AppSettings
    repository: SQLiteRepository
    file_importer: FileImporter = field(default_factory=FileImporter)
    normalizer: PatentNormalizer = field(default_factory=PatentNormalizer)

    @classmethod
    def from_settings(cls, settings: AppSettings | None = None) -> "PipelineService":
        """Build the service from application settings."""
        resolved_settings = settings or AppSettings()
        repository = SQLiteRepository(resolved_settings.storage.database_path)
        return cls(settings=resolved_settings, repository=repository)

    def initialize_storage(self) -> Path:
        """Initialize local storage and return the database path."""
        self.repository.initialize()
        return self.repository.database_path

    def ensure_canonical_corpus_loaded(self) -> dict[str, Any]:
        """Ensure SQLite mirrors the canonical curated CSV corpus."""
        self.repository.initialize()
        canonical_path = self._canonical_corpus_path()
        if not canonical_path.exists():
            raise FileNotFoundError(f"Canonical corpus not found at {canonical_path}.")

        source_file_hash = self._source_file_hash(canonical_path)
        normalized_records, canonical_summary = self._prepare_prepared_source_dataset(
            canonical_path
        )
        row_hashes = self.repository.row_hashes_for_records(normalized_records)
        corpus_hash = self.repository.corpus_hash_for_row_hashes(row_hashes)
        current_records = self.repository.fetch_all_patents()
        current_source_counts = self._source_counts_for_records(current_records)
        expected_source_counts = self._nonzero_source_counts(
            canonical_summary["source_counts"]
        )
        active_corpus_version = self.repository.get_active_corpus_version()
        current_hash_index = self.repository.fetch_patent_hash_index()
        expected_hash_index = dict(sorted(row_hashes.items()))
        expected_by_analysis_id = {
            record.analysis_id: record for record in normalized_records
        }
        current_by_analysis_id = {
            record.analysis_id: record for record in current_records
        }
        sync_reason = self._canonical_sync_reason(
            current_records=current_records,
            current_source_counts=current_source_counts,
            expected_records=normalized_records,
            expected_source_counts=expected_source_counts,
            current_by_analysis_id=current_by_analysis_id,
            expected_by_analysis_id=expected_by_analysis_id,
        )
        active_matches = (
            active_corpus_version is not None
            and active_corpus_version["corpus_hash"] == corpus_hash
        )
        hash_index_matches = current_hash_index == expected_hash_index
        if active_matches and hash_index_matches:
            sync_reason = "already_current"
        elif sync_reason == "already_current" and active_corpus_version is None:
            sync_reason = "no_active_corpus_version"
        elif sync_reason == "already_current" and not active_matches:
            sync_reason = "active_corpus_hash_mismatch"
        elif sync_reason == "already_current" and not hash_index_matches:
            sync_reason = "patent_hash_index_mismatch"

        canonical_summary.update(
            {
                "canonical_path": str(canonical_path),
                "source_path": str(canonical_path),
                "source_file_hash": source_file_hash,
                "corpus_hash": corpus_hash,
                "row_hash_version": self.repository.ROW_HASH_VERSION,
                "hash_algorithm": self.repository.HASH_ALGORITHM,
                "previous_total_patents": len(current_records),
                "previous_source_counts": current_source_counts,
                "sync_reason": sync_reason,
                "import_batch_id": None,
                "corpus_version_id": (
                    active_corpus_version["id"] if active_corpus_version else None
                ),
            }
        )
        if sync_reason == "already_current":
            metadata_action = self._refresh_active_canonical_metadata_if_needed(
                active_corpus_version=active_corpus_version,
                canonical_summary=canonical_summary,
                canonical_path=canonical_path,
                source_file_hash=source_file_hash,
                corpus_hash=corpus_hash,
                source_counts=canonical_summary["source_counts"],
                row_count=len(normalized_records),
            )
            if metadata_action == "updated_canonical_metadata":
                canonical_summary["sync_reason"] = "already_current_metadata_refreshed"
                canonical_summary["metadata_action"] = metadata_action
            canonical_summary["sync_action"] = "skipped"
            canonical_summary["upserted_rows"] = 0
            canonical_summary["inserted_rows"] = 0
            canonical_summary["updated_rows"] = 0
            canonical_summary["unchanged_rows"] = len(normalized_records)
            canonical_summary["deleted_rows"] = 0
            canonical_summary["pruned_rows"] = 0
            return canonical_summary

        import_batch_id = self.repository.create_import_batch(
            workflow="startup_sync",
            dataset_kind="canonical_corpus",
            source_label="canonical",
            source_path=str(canonical_path),
            source_file_hash=source_file_hash,
            corpus_hash=corpus_hash,
            total_raw_rows=canonical_summary["total_raw_rows"],
            valid_normalized_rows=canonical_summary["valid_normalized_rows"],
            skipped_rows=canonical_summary["skipped_rows"],
            summary=canonical_summary,
        )
        canonical_summary["import_batch_id"] = import_batch_id
        try:
            corpus_version = self.repository.get_or_create_corpus_version(
                corpus_hash=corpus_hash,
                dataset_kind="prepared_source",
                source_label=canonical_summary["source"],
                label=f"canonical-corpus-{corpus_hash[:12]}",
                source_path=str(canonical_path),
                source_file_hash=source_file_hash,
                source_counts=canonical_summary["source_counts"],
                summary=canonical_summary,
                row_count=len(normalized_records),
                created_from_import_batch_id=import_batch_id,
            )
            corpus_version_id = int(corpus_version["id"])
            counts = self.repository.replace_patents_for_corpus(
                normalized_records,
                row_hashes,
                import_batch_id,
                corpus_version_id,
            )
            self.repository.activate_corpus_version(corpus_version_id)
            canonical_summary.update(counts)
            canonical_summary["corpus_version_id"] = corpus_version_id
            canonical_summary["sync_action"] = "reloaded_canonical_corpus"
            self.repository.complete_import_batch(
                import_batch_id,
                corpus_version_id=corpus_version_id,
                total_raw_rows=canonical_summary["total_raw_rows"],
                valid_normalized_rows=canonical_summary["valid_normalized_rows"],
                skipped_rows=canonical_summary["skipped_rows"],
                upserted_rows=counts["upserted_rows"],
                inserted_rows=counts["inserted_rows"],
                updated_rows=counts["updated_rows"],
                unchanged_rows=counts["unchanged_rows"],
                summary=canonical_summary,
            )
        except Exception as exc:
            self.repository.fail_import_batch(
                import_batch_id,
                error_message=str(exc),
                summary=canonical_summary,
            )
            raise

        return canonical_summary

    def import_patents(
        self, file_source: FileInput, import_type: str | None = None
    ) -> dict[str, Any]:
        """Import a CSV/JSON file into SQLite and return count details."""
        self.repository.initialize()
        source_type = self._source_type_for_import(file_source, import_type)
        source_path = self._source_path_for_file_input(file_source)
        source_file_hash = self._source_file_hash(file_source)
        raw_records = self.file_importer.import_file(file_source, import_type)

        return self._normalize_and_store(
            raw_records,
            source_for_row=lambda _raw_record: source_type,
            source_label=source_type.value,
            dataset_kind="manual_import",
            source_path=source_path,
            source_file_hash=source_file_hash,
        )

    def load_sample_recovery_corpus(self) -> dict[str, Any]:
        """Load the canonical corpus through the sample/recovery workflow."""
        sample_path = (
            Path(self.settings.storage.raw_data_dir) / SAMPLE_RECOVERY_CORPUS_FILENAME
        )
        if not sample_path.exists():
            raise FileNotFoundError(f"Canonical corpus not found at {sample_path}.")

        return self.import_prepared_source_dataset(sample_path)

    def load_demo_dataset(self) -> dict[str, Any]:
        """Compatibility wrapper for the legacy sample/recovery route."""
        return self.load_sample_recovery_corpus()

    def load_prepared_source_dataset(self) -> dict[str, Any]:
        """Load the curated source-labeled CSV dataset into SQLite."""
        source_dataset_path = (
            Path(self.settings.storage.raw_data_dir) / PREPARED_SOURCE_DATASET_FILENAME
        )
        if not source_dataset_path.exists():
            raise FileNotFoundError(
                "Prepared curated patent dataset not found at "
                f"{source_dataset_path}."
            )

        return self.import_prepared_source_dataset(source_dataset_path)

    def import_prepared_source_dataset(
        self, file_source: FileInput, import_type: str | None = "csv"
    ) -> dict[str, Any]:
        """Import a curated CSV while preserving row-level public source labels."""
        self.repository.initialize()
        normalized_records, summary = self._prepare_prepared_source_dataset(
            file_source,
            import_type=import_type,
            empty_message=(
                "The prepared curated patent dataset is ready to be filled with "
                "manually collected and verified records from public patent sources."
            ),
        )
        row_hashes = self.repository.row_hashes_for_records(normalized_records)
        corpus_hash = self.repository.corpus_hash_for_row_hashes(row_hashes)
        source_path = self._source_path_for_file_input(file_source)
        source_file_hash = self._source_file_hash(file_source)
        current_hash_index = self.repository.fetch_patent_hash_index()
        expected_hash_index = dict(sorted(row_hashes.items()))
        active_corpus_version = self.repository.get_active_corpus_version()
        active_matches = (
            active_corpus_version is not None
            and active_corpus_version["corpus_hash"] == corpus_hash
        )
        hash_index_matches = current_hash_index == expected_hash_index
        summary.update(
            {
                "source_path": source_path,
                "source_file_hash": source_file_hash,
                "corpus_hash": corpus_hash,
                "row_hash_version": self.repository.ROW_HASH_VERSION,
                "hash_algorithm": self.repository.HASH_ALGORITHM,
                "import_batch_id": None,
                "corpus_version_id": (
                    active_corpus_version["id"] if active_corpus_version else None
                ),
            }
        )
        import_batch_id = self.repository.create_import_batch(
            workflow="load_prepared",
            dataset_kind="prepared_source",
            source_label=summary["source"],
            source_path=source_path,
            source_file_hash=source_file_hash,
            corpus_hash=corpus_hash,
            total_raw_rows=summary["total_raw_rows"],
            valid_normalized_rows=summary["valid_normalized_rows"],
            skipped_rows=summary["skipped_rows"],
            summary=summary,
        )
        summary["import_batch_id"] = import_batch_id
        if active_matches and hash_index_matches:
            summary.update(
                {
                    "sync_action": "skipped",
                    "sync_reason": "already_current",
                    "upserted_rows": 0,
                    "inserted_rows": 0,
                    "updated_rows": 0,
                    "unchanged_rows": len(normalized_records),
                    "deleted_rows": 0,
                    "pruned_rows": 0,
                }
            )
            self.repository.skip_import_batch(
                import_batch_id,
                corpus_version_id=int(active_corpus_version["id"]),
                total_raw_rows=summary["total_raw_rows"],
                valid_normalized_rows=summary["valid_normalized_rows"],
                skipped_rows=summary["skipped_rows"],
                summary=summary,
            )
            return summary

        try:
            corpus_version = self.repository.get_or_create_corpus_version(
                corpus_hash=corpus_hash,
                dataset_kind="prepared_source",
                source_label=summary["source"],
                label=f"prepared-source-{corpus_hash[:12]}",
                source_path=source_path,
                source_file_hash=source_file_hash,
                source_counts=self._nonzero_source_counts(summary["source_counts"]),
                summary=summary,
                row_count=len(normalized_records),
                created_from_import_batch_id=import_batch_id,
            )
            corpus_version_id = int(corpus_version["id"])
            counts = self.repository.replace_patents_for_corpus(
                normalized_records,
                row_hashes,
                import_batch_id,
                corpus_version_id,
            )
            self.repository.activate_corpus_version(corpus_version_id)
            summary.update(counts)
            summary["corpus_version_id"] = corpus_version_id
            summary["sync_action"] = "loaded_prepared_source_dataset"
            summary["sync_reason"] = (
                "sqlite_empty" if not current_hash_index else "corpus_changed"
            )
            self.repository.complete_import_batch(
                import_batch_id,
                corpus_version_id=corpus_version_id,
                total_raw_rows=summary["total_raw_rows"],
                valid_normalized_rows=summary["valid_normalized_rows"],
                skipped_rows=summary["skipped_rows"],
                upserted_rows=counts["upserted_rows"],
                inserted_rows=counts["inserted_rows"],
                updated_rows=counts["updated_rows"],
                unchanged_rows=counts["unchanged_rows"],
                summary=summary,
            )
        except Exception as exc:
            self.repository.fail_import_batch(
                import_batch_id,
                error_message=str(exc),
                summary=summary,
            )
            raise
        return summary

    def fetch_saved_patents(self) -> list[PatentRecord]:
        """Fetch saved patents for app preview."""
        return self.repository.fetch_all_patents()

    def _normalize_and_store(
        self,
        raw_records: list[dict[str, Any]],
        *,
        source_for_row: Callable[[dict[str, Any]], SourceType],
        source_label: str,
        dataset_kind: str,
        source_path: str | None = None,
        source_file_hash: str | None = None,
        source_counts: dict[str, int] | None = None,
        empty_message: str | None = None,
    ) -> dict[str, Any]:
        normalized_records = []
        warnings: list[str] = []
        for row_number, raw_record in enumerate(raw_records, start=1):
            try:
                source_type = source_for_row(raw_record)
                normalized_record = self.normalizer.normalize(raw_record, source_type)
            except ValueError as exc:
                warnings.append(f"Row {row_number}: {exc}")
                continue

            normalized_records.append(normalized_record)
            if source_counts is not None:
                source_counts[normalized_record.source.value] = (
                    source_counts.get(normalized_record.source.value, 0) + 1
                )

        row_hashes = self.repository.row_hashes_for_records(normalized_records)
        summary: dict[str, Any] = {
            "source": source_label,
            "dataset_kind": dataset_kind,
            "total_raw_rows": len(raw_records),
            "valid_normalized_rows": len(normalized_records),
            "skipped_rows": len(raw_records) - len(normalized_records),
            "upserted_rows": 0,
            "warnings": warnings,
            "errors": [],
            "source_path": source_path,
            "source_file_hash": source_file_hash,
            "row_hash_version": self.repository.ROW_HASH_VERSION,
            "hash_algorithm": self.repository.HASH_ALGORITHM,
            "import_batch_id": None,
            "corpus_version_id": None,
        }
        if source_counts is not None:
            summary["source_counts"] = source_counts
        if empty_message and not raw_records:
            summary["message"] = empty_message

        import_batch_id = self.repository.create_import_batch(
            workflow="manual_import",
            dataset_kind=dataset_kind,
            source_label=source_label,
            source_path=source_path,
            source_file_hash=source_file_hash,
            total_raw_rows=summary["total_raw_rows"],
            valid_normalized_rows=summary["valid_normalized_rows"],
            skipped_rows=summary["skipped_rows"],
            summary=summary,
        )
        summary["import_batch_id"] = import_batch_id
        try:
            counts = self.repository.upsert_patents_with_import_metadata(
                normalized_records,
                row_hashes,
                import_batch_id,
                corpus_version_id=None,
            )
            summary.update(counts)
            summary["sync_action"] = "imported"
            self.repository.complete_import_batch(
                import_batch_id,
                total_raw_rows=summary["total_raw_rows"],
                valid_normalized_rows=summary["valid_normalized_rows"],
                skipped_rows=summary["skipped_rows"],
                upserted_rows=counts["upserted_rows"],
                inserted_rows=counts["inserted_rows"],
                updated_rows=counts["updated_rows"],
                unchanged_rows=counts["unchanged_rows"],
                summary=summary,
            )
        except Exception as exc:
            self.repository.fail_import_batch(
                import_batch_id,
                error_message=str(exc),
                summary=summary,
            )
            raise

        return summary

    def _prepare_prepared_source_dataset(
        self,
        file_source: FileInput,
        import_type: str | None = "csv",
        *,
        empty_message: str | None = None,
    ) -> tuple[list[PatentRecord], dict[str, Any]]:
        self._validate_prepared_source_columns(file_source, import_type)
        raw_records = self.file_importer.import_file(file_source, import_type)
        source_counts = self._empty_prepared_source_counts()
        normalized_records, warnings = self._normalize_records(
            raw_records,
            source_for_row=self._source_type_from_prepared_row,
            source_counts=source_counts,
        )
        summary: dict[str, Any] = {
            "source": "EPO / USPTO / TURKPATENT",
            "dataset_kind": "prepared_source",
            "total_raw_rows": len(raw_records),
            "valid_normalized_rows": len(normalized_records),
            "skipped_rows": len(raw_records) - len(normalized_records),
            "upserted_rows": 0,
            "warnings": warnings,
            "errors": [],
            "source_counts": source_counts,
        }
        if empty_message and not raw_records:
            summary["message"] = empty_message

        return normalized_records, summary

    def _normalize_records(
        self,
        raw_records: list[dict[str, Any]],
        *,
        source_for_row: Callable[[dict[str, Any]], SourceType],
        source_counts: dict[str, int] | None = None,
    ) -> tuple[list[PatentRecord], list[str]]:
        normalized_records = []
        warnings: list[str] = []
        for row_number, raw_record in enumerate(raw_records, start=1):
            try:
                source_type = source_for_row(raw_record)
                normalized_record = self.normalizer.normalize(raw_record, source_type)
            except ValueError as exc:
                warnings.append(f"Row {row_number}: {exc}")
                continue

            normalized_records.append(normalized_record)
            if source_counts is not None:
                source_counts[normalized_record.source.value] = (
                    source_counts.get(normalized_record.source.value, 0) + 1
                )

        return normalized_records, warnings

    def _canonical_corpus_path(self) -> Path:
        return Path(self.settings.storage.raw_data_dir) / CANONICAL_CORPUS_FILENAME

    def _source_path_for_file_input(self, file_source: FileInput) -> str | None:
        if isinstance(file_source, (str, PathLike)):
            return str(Path(file_source))
        return None

    def _source_file_hash(self, file_source: FileInput) -> str | None:
        content = self._source_file_bytes(file_source)
        if content is None:
            return None
        return hashlib.sha256(content).hexdigest()

    def _source_file_bytes(self, file_source: FileInput) -> bytes | None:
        if isinstance(file_source, (str, PathLike)):
            path = Path(file_source)
            if path.exists() and path.is_file():
                return path.read_bytes()
            return None

        if hasattr(file_source, "getvalue"):
            content = file_source.getvalue()
        elif hasattr(file_source, "read"):
            position = None
            if hasattr(file_source, "tell"):
                try:
                    position = file_source.tell()
                except OSError:
                    position = None
            if hasattr(file_source, "seek"):
                try:
                    file_source.seek(0)
                except OSError:
                    pass
            content = file_source.read()
            if position is not None and hasattr(file_source, "seek"):
                try:
                    file_source.seek(position)
                except OSError:
                    pass
        else:
            return None

        if isinstance(content, bytes):
            return content
        if isinstance(content, str):
            return content.encode(self.file_importer.encoding)
        return None

    def _canonical_sync_reason(
        self,
        *,
        current_records: list[PatentRecord],
        current_source_counts: dict[str, int],
        expected_records: list[PatentRecord],
        expected_source_counts: dict[str, int],
        current_by_analysis_id: dict[str, PatentRecord],
        expected_by_analysis_id: dict[str, PatentRecord],
    ) -> str:
        if not current_records:
            return "sqlite_empty"
        if len(expected_records) > len(current_records):
            return "canonical_has_more_records"
        if len(expected_records) != len(current_records):
            return "runtime_count_mismatch"
        if current_source_counts != expected_source_counts:
            return "source_distribution_mismatch"
        if current_by_analysis_id != expected_by_analysis_id:
            return "canonical_records_changed"
        return "already_current"

    def _source_counts_for_records(self, records: list[PatentRecord]) -> dict[str, int]:
        return {
            source_type.value: sum(
                1 for record in records if record.source == source_type
            )
            for source_type in SourceType
            if any(record.source == source_type for record in records)
        }

    def _nonzero_source_counts(self, source_counts: dict[str, int]) -> dict[str, int]:
        return {source: count for source, count in source_counts.items() if count}

    def _refresh_active_canonical_metadata_if_needed(
        self,
        *,
        active_corpus_version: dict[str, Any] | None,
        canonical_summary: dict[str, Any],
        canonical_path: Path,
        source_file_hash: str | None,
        corpus_hash: str,
        source_counts: dict[str, int],
        row_count: int,
    ) -> str | None:
        if active_corpus_version is None:
            return None

        expected_summary = {
            **canonical_summary,
            "metadata_action": "updated_canonical_metadata",
        }
        if not self._active_corpus_metadata_needs_refresh(
            active_corpus_version,
            canonical_path=canonical_path,
            source_file_hash=source_file_hash,
            corpus_hash=corpus_hash,
            source_counts=source_counts,
            source_label=canonical_summary["source"],
        ):
            return None

        self.repository.update_corpus_version_metadata(
            int(active_corpus_version["id"]),
            dataset_kind="prepared_source",
            source_label=canonical_summary["source"],
            source_path=str(canonical_path),
            source_file_hash=source_file_hash,
            source_counts=source_counts,
            summary=expected_summary,
            row_count=row_count,
        )
        return "updated_canonical_metadata"

    def _active_corpus_metadata_needs_refresh(
        self,
        active_corpus_version: dict[str, Any],
        *,
        canonical_path: Path,
        source_file_hash: str | None,
        corpus_hash: str,
        source_counts: dict[str, int],
        source_label: str,
    ) -> bool:
        if active_corpus_version.get("dataset_kind") != "prepared_source":
            return True
        if active_corpus_version.get("source_label") != source_label:
            return True
        if active_corpus_version.get("source_file_hash") != source_file_hash:
            return True
        if (
            self._loads_summary_dict(active_corpus_version.get("source_counts_json"))
            != source_counts
        ):
            return True

        summary = self._loads_summary_dict(active_corpus_version.get("summary_json"))
        expected_summary_fields = {
            "canonical_path": str(canonical_path),
            "source_path": str(canonical_path),
            "source_file_hash": source_file_hash,
            "corpus_hash": corpus_hash,
        }
        return any(
            summary.get(field_name) != expected_value
            for field_name, expected_value in expected_summary_fields.items()
        )

    def _loads_summary_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not isinstance(value, str) or not value:
            return {}
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _source_type_for_import(
        self, file_source: FileInput, import_type: str | None
    ) -> SourceType:
        extension = self.file_importer.resolve_extension(file_source, import_type)
        if extension == ".csv":
            return SourceType.CSV_IMPORT
        if extension == ".json":
            return SourceType.JSON_IMPORT

        raise ValueError(f"Unsupported import file type '{extension}'.")

    def _validate_prepared_source_columns(
        self, file_source: FileInput, import_type: str | None
    ) -> None:
        headers = self.file_importer.read_csv_headers(file_source, import_type)
        canonical_headers = {self._canonical_column_name(header) for header in headers}
        missing_columns = [
            column
            for column in PREPARED_SOURCE_DATASET_REQUIRED_COLUMNS
            if self._canonical_column_name(column) not in canonical_headers
        ]
        if missing_columns:
            missing_text = ", ".join(missing_columns)
            raise ValueError(
                "Prepared curated patent dataset is missing required column(s): "
                f"{missing_text}."
            )

    def _source_type_from_prepared_row(self, raw_record: dict[str, Any]) -> SourceType:
        source_value = self._value_for_column(raw_record, "source")
        if source_value is None or not str(source_value).strip():
            raise ValueError("Missing required field: source.")

        source_key = self._canonical_source_label(str(source_value))
        source_type = PREPARED_SOURCE_LABEL_ALIASES.get(source_key)
        if source_type is None:
            raise ValueError(
                "Unsupported prepared source label: "
                f"{source_value}. Expected EPO, USPTO, TURKPATENT, or TPO."
            )

        return source_type

    def _value_for_column(self, raw_record: dict[str, Any], column_name: str) -> Any:
        canonical_column = self._canonical_column_name(column_name)
        for key, value in raw_record.items():
            if self._canonical_column_name(str(key)) == canonical_column:
                return value
        return None

    def _empty_prepared_source_counts(self) -> dict[str, int]:
        return {source_type.value: 0 for source_type in PREPARED_SOURCE_TYPES}

    def _canonical_column_name(self, value: str) -> str:
        return value.strip().lower().replace("-", "_").replace(" ", "_")

    def _canonical_source_label(self, value: str) -> str:
        return (
            value.strip().upper().replace("-", "_").replace(" ", "_").replace("/", "_")
        )
