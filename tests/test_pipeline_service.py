"""Tests for the manual import pipeline service."""

import json
import sqlite3
from collections import Counter

import pytest

from src.acquisition.corpus_quality import (
    CANONICAL_CORPUS_ACCEPTED_REQUIRED_FIELDS,
    CANONICAL_CORPUS_CLASSIFICATION_FIELDS,
    CANONICAL_CORPUS_STRONGLY_PREFERRED_FIELDS,
    REVIEW_NEEDED_SCHEMA_COLUMNS,
    audit_corpus_row,
)
from src.acquisition.file_importer import FileImporter
from src.config.settings import AppSettings, StorageConfig
from src.models.enums import SourceType
from src.models.patent import PatentRecord
from src.services.pipeline_service import (
    CANONICAL_CORPUS_CRITICAL_FIELDS,
    CANONICAL_CORPUS_FILENAME,
    CANONICAL_CORPUS_SCHEMA_COLUMNS,
    PREPARED_SOURCE_DATASET_REQUIRED_COLUMNS,
    PipelineService,
)
from src.storage.sqlite_repository import SQLiteRepository
from src.utils.paths import data_path


def _canonical_records() -> list[dict[str, object]]:
    source_path = data_path("raw", "fiber_wearable_patents_sources.csv")
    return FileImporter().import_file(source_path)


def _write_canonical_source_csv(raw_dir, rows: list[dict[str, str]]) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    csv_path = raw_dir / CANONICAL_CORPUS_FILENAME
    lines = [",".join(CANONICAL_CORPUS_SCHEMA_COLUMNS)]
    for row in rows:
        lines.append(
            ",".join(row.get(column, "") for column in CANONICAL_CORPUS_SCHEMA_COLUMNS)
        )
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _isolated_service(tmp_path) -> PipelineService:
    settings = AppSettings(
        storage=StorageConfig(
            database_path=tmp_path / "processed" / "patents.sqlite3",
            raw_data_dir=tmp_path / "raw",
            processed_data_dir=tmp_path / "processed",
            exports_dir=tmp_path / "exports",
        )
    )
    return PipelineService(
        settings=settings,
        repository=SQLiteRepository(settings.storage.database_path),
    )


def _table_count(database_path, table_name: str) -> int:
    with sqlite3.connect(database_path) as connection:
        return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def _patent_metadata_rows(database_path) -> list[tuple[object, ...]]:
    with sqlite3.connect(database_path) as connection:
        return connection.execute("""
            SELECT
                patent_id,
                source,
                import_batch_id,
                corpus_version_id,
                row_hash,
                updated_at
            FROM patents
            ORDER BY patent_id, source
            """).fetchall()


def _active_corpus_metadata(database_path) -> dict[str, object]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("""
            SELECT *
            FROM corpus_versions
            WHERE is_active = 1
            ORDER BY activated_at DESC, id DESC
            LIMIT 1
            """).fetchone()
    assert row is not None
    return dict(row)


def test_canonical_corpus_schema_expectations_are_documented() -> None:
    expected_schema = (
        "source",
        "patent_id",
        "publication_number",
        "title",
        "abstract",
        "assignee",
        "inventors",
        "publication_date",
        "filing_date",
        "country",
        "source_url",
        "keywords",
        "candidate_application_areas",
        "ipc_codes",
        "cpc_codes",
        "claims_excerpt",
        "patent_family",
        "citation_count",
    )

    assert CANONICAL_CORPUS_SCHEMA_COLUMNS == expected_schema
    assert CANONICAL_CORPUS_CRITICAL_FIELDS == CANONICAL_CORPUS_ACCEPTED_REQUIRED_FIELDS
    assert CANONICAL_CORPUS_CLASSIFICATION_FIELDS == ("ipc_codes", "cpc_codes")
    assert CANONICAL_CORPUS_STRONGLY_PREFERRED_FIELDS == (
        "claims_excerpt",
        "patent_family",
        "citation_count",
    )
    assert REVIEW_NEEDED_SCHEMA_COLUMNS == (
        *CANONICAL_CORPUS_SCHEMA_COLUMNS,
        "review_reason",
        "missing_fields",
        "source_notes",
    )
    assert set(CANONICAL_CORPUS_CRITICAL_FIELDS).issubset(
        CANONICAL_CORPUS_SCHEMA_COLUMNS
    )
    assert set(PREPARED_SOURCE_DATASET_REQUIRED_COLUMNS).issubset(
        CANONICAL_CORPUS_SCHEMA_COLUMNS
    )


def test_prepared_source_dataset_file_has_curated_records() -> None:
    source_path = data_path("raw", "fiber_wearable_patents_sources.csv")

    assert source_path.exists()

    headers = FileImporter().read_csv_headers(source_path)
    records = FileImporter().import_file(source_path)
    required_nonblank_fields = (
        "patent_id",
        "source",
        "title",
        "abstract",
        "source_url",
    )
    patent_ids = [str(record["patent_id"]).strip() for record in records]

    source_counts = Counter(str(record["source"]).strip() for record in records)

    assert headers == list(CANONICAL_CORPUS_SCHEMA_COLUMNS)
    assert len(records) >= 50
    assert set(source_counts).issubset({"USPTO", "EPO", "TURKPATENT"})
    assert {"USPTO", "EPO", "TURKPATENT"}.issubset(source_counts)
    for record in records:
        for field in required_nonblank_fields:
            assert str(record.get(field, "")).strip()
    assert len(patent_ids) == len(set(patent_ids))


def test_review_needed_file_uses_expected_schema() -> None:
    review_path = data_path("raw", "patent_collection_review_needed.csv")
    accepted_publication_numbers = {
        str(record["publication_number"]).strip() for record in _canonical_records()
    }

    assert review_path.exists()
    headers = FileImporter().read_csv_headers(review_path)
    assert len(REVIEW_NEEDED_SCHEMA_COLUMNS) == 21
    assert headers == list(REVIEW_NEEDED_SCHEMA_COLUMNS)
    records = FileImporter().import_file(review_path)
    publication_numbers = [
        str(record["publication_number"]).strip() for record in records
    ]

    assert records
    for record in records:
        assert tuple(record) == REVIEW_NEEDED_SCHEMA_COLUMNS
        assert str(record["review_reason"]).strip()
        assert str(record["source_notes"]).strip()
    assert not (set(publication_numbers) & accepted_publication_numbers)


def test_pipeline_imports_csv_and_skips_bad_rows(tmp_path) -> None:
    csv_path = tmp_path / "patents.csv"
    csv_path.write_text(
        "patent_id,title,abstract,inventors,ipc_codes\n"
        "US-1,Fiber sensor,Wearable electronics,Ada Example; Bob Example,A61B|G06F\n"
        "US-2,,Missing title,Ada Example,A61B\n",
        encoding="utf-8",
    )
    service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )

    summary = service.import_patents(csv_path)

    assert summary["source"] == SourceType.CSV_IMPORT.value
    assert summary["total_raw_rows"] == 2
    assert summary["valid_normalized_rows"] == 1
    assert summary["skipped_rows"] == 1
    assert summary["upserted_rows"] == 1
    assert len(summary["warnings"]) == 1
    assert service.repository.count_patents() == 1

    saved_record = service.repository.fetch_all_patents()[0]
    assert saved_record.patent_id == "US-1"
    assert saved_record.inventors == ["Ada Example", "Bob Example"]
    assert saved_record.ipc_codes == ["A61B", "G06F"]


def test_pipeline_load_sample_recovery_corpus_imports_and_upserts(
    tmp_path,
) -> None:
    expected_count = len(_canonical_records())
    service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )

    first_summary = service.load_sample_recovery_corpus()
    first_count = service.repository.count_patents()
    second_summary = service.load_demo_dataset()

    assert first_summary["dataset_kind"] == "prepared_source"
    assert first_summary["source"] == "EPO / USPTO / TURKPATENT"
    assert first_summary["total_raw_rows"] == first_count
    assert first_summary["valid_normalized_rows"] == first_count
    assert first_summary["skipped_rows"] == 0
    assert first_count == expected_count
    assert first_count >= 50

    assert second_summary["sync_action"] == "skipped"
    assert second_summary["sync_reason"] == "already_current"
    assert second_summary["upserted_rows"] == 0
    assert second_summary["unchanged_rows"] == first_count
    assert second_summary["import_batch_id"] is not None
    assert service.repository.count_patents() == first_count


def test_pipeline_loads_prepared_source_dataset_imports_and_upserts(
    tmp_path,
) -> None:
    expected_count = len(_canonical_records())
    service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )

    first_summary = service.load_prepared_source_dataset()
    first_count = service.repository.count_patents()
    first_patent_metadata = _patent_metadata_rows(service.repository.database_path)
    second_summary = service.load_prepared_source_dataset()

    assert first_summary["dataset_kind"] == "prepared_source"
    assert first_summary["total_raw_rows"] == expected_count
    assert first_summary["valid_normalized_rows"] == expected_count
    assert first_summary["skipped_rows"] == 0
    assert first_summary["upserted_rows"] == expected_count
    assert set(first_summary["source_counts"]) == {"EPO", "USPTO", "TURKPATENT"}
    assert sum(first_summary["source_counts"].values()) == expected_count
    assert first_count == expected_count
    assert first_count >= 50
    assert second_summary["sync_action"] == "skipped"
    assert second_summary["sync_reason"] == "already_current"
    assert second_summary["upserted_rows"] == 0
    assert second_summary["unchanged_rows"] == expected_count
    assert second_summary["import_batch_id"] is not None
    assert service.repository.count_patents() == expected_count
    assert (
        _patent_metadata_rows(service.repository.database_path) == first_patent_metadata
    )
    with sqlite3.connect(service.repository.database_path) as connection:
        skipped_status = connection.execute(
            """
            SELECT status
            FROM import_batches
            WHERE id = ?
            """,
            (second_summary["import_batch_id"],),
        ).fetchone()[0]
    assert skipped_status == "skipped"


def test_pipeline_ensure_canonical_corpus_reloads_stale_sqlite(tmp_path) -> None:
    service = _isolated_service(tmp_path)
    _write_canonical_source_csv(
        service.settings.storage.raw_data_dir,
        [
            {
                "source": "USPTO",
                "patent_id": "US-CANONICAL-1",
                "publication_number": "US-CANONICAL-1",
                "title": "Conductive yarn garment",
                "abstract": "A wearable textile sensor.",
                "assignee": "Fiber Labs",
                "inventors": "Ada Example",
                "publication_date": "2024-01-01",
                "filing_date": "2023-01-01",
                "country": "US",
                "source_url": "https://example.test/us",
                "keywords": "fiber; sensor",
            },
            {
                "source": "EPO",
                "patent_id": "EP-CANONICAL-1",
                "publication_number": "EP-CANONICAL-1",
                "title": "Textile electrode system",
                "abstract": "A wearable textile electrode.",
                "assignee": "Weave Labs",
                "inventors": "Bora Example",
                "publication_date": "2024-02-01",
                "filing_date": "2023-02-01",
                "country": "EP",
                "source_url": "https://example.test/ep",
                "keywords": "textile; electrode",
            },
            {
                "source": "TURKPATENT",
                "patent_id": "TR-CANONICAL-1",
                "publication_number": "TR-CANONICAL-1",
                "title": "Movement tracking fabric",
                "abstract": "A smart garment for rehabilitation.",
                "assignee": "Rehab Textiles",
                "inventors": "Cem Example",
                "publication_date": "2024-03-01",
                "filing_date": "2023-03-01",
                "country": "TR",
                "source_url": "https://example.test/tr",
                "keywords": "movement; fabric",
            },
        ],
    )
    service.repository.upsert_patents(
        [
            PatentRecord(
                patent_id="US-STALE-1",
                source=SourceType.USPTO,
                title="Old runtime row",
                abstract="This stale row should be replaced.",
            )
        ]
    )

    summary = service.ensure_canonical_corpus_loaded()

    assert summary["sync_action"] == "reloaded_canonical_corpus"
    assert summary["sync_reason"] == "canonical_has_more_records"
    assert summary["previous_total_patents"] == 1
    assert summary["upserted_rows"] == 3
    assert summary["pruned_rows"] == 1
    assert summary["corpus_hash"]
    assert summary["corpus_version_id"] is not None
    assert summary["source_file_hash"]
    assert summary["source_counts"] == {"EPO": 1, "USPTO": 1, "TURKPATENT": 1}
    assert service.repository.count_patents() == 3
    assert all(service.repository.fetch_patent_hash_index().values())
    assert {record.patent_id for record in service.repository.fetch_all_patents()} == {
        "US-CANONICAL-1",
        "EP-CANONICAL-1",
        "TR-CANONICAL-1",
    }


def test_pipeline_ensure_canonical_corpus_skips_current_sqlite(tmp_path) -> None:
    service = _isolated_service(tmp_path)
    _write_canonical_source_csv(
        service.settings.storage.raw_data_dir,
        [
            {
                "source": "USPTO",
                "patent_id": "US-CURRENT-1",
                "publication_number": "US-CURRENT-1",
                "title": "Conductive yarn garment",
                "abstract": "A wearable textile sensor.",
                "assignee": "Fiber Labs",
                "inventors": "Ada Example",
                "publication_date": "2024-01-01",
                "filing_date": "2023-01-01",
                "country": "US",
                "source_url": "https://example.test/us",
                "keywords": "fiber; sensor",
                "candidate_application_areas": "Healthcare monitoring; Smart garments",
                "claims_excerpt": "a textile sensor claim",
                "patent_family": "12345",
                "citation_count": "7",
            }
        ],
    )

    first_summary = service.ensure_canonical_corpus_loaded()
    import_batch_count_after_first = _table_count(
        service.repository.database_path, "import_batches"
    )
    corpus_version_count_after_first = _table_count(
        service.repository.database_path, "corpus_versions"
    )
    second_summary = service.ensure_canonical_corpus_loaded()

    assert first_summary["sync_action"] == "reloaded_canonical_corpus"
    assert first_summary["sync_reason"] == "sqlite_empty"
    assert first_summary["corpus_hash"]
    assert first_summary["corpus_version_id"] is not None
    assert first_summary["source_file_hash"]
    assert second_summary["sync_action"] == "skipped"
    assert second_summary["sync_reason"] == "already_current"
    assert second_summary["upserted_rows"] == 0
    assert second_summary["import_batch_id"] is None
    assert second_summary["corpus_hash"] == first_summary["corpus_hash"]
    assert (
        _table_count(service.repository.database_path, "import_batches")
        == import_batch_count_after_first
    )
    assert (
        _table_count(service.repository.database_path, "corpus_versions")
        == corpus_version_count_after_first
    )
    assert service.repository.count_patents() == 1
    saved_record = service.repository.fetch_all_patents()[0]
    assert saved_record.publication_number == "US-CURRENT-1"
    assert saved_record.candidate_application_areas == [
        "Healthcare monitoring",
        "Smart garments",
    ]
    assert saved_record.claims_excerpt == "a textile sensor claim"
    assert saved_record.patent_family == "12345"
    assert saved_record.citation_count == 7


def test_startup_refreshes_matching_legacy_corpus_metadata_without_reimport(
    tmp_path,
) -> None:
    service = _isolated_service(tmp_path)
    _write_canonical_source_csv(
        service.settings.storage.raw_data_dir,
        [
            {
                "source": "USPTO",
                "patent_id": "US-LEGACY-CURRENT-1",
                "publication_number": "US-LEGACY-CURRENT-1",
                "title": "Conductive yarn garment",
                "abstract": "A wearable textile sensor.",
                "assignee": "Fiber Labs",
                "inventors": "Ada Example",
                "publication_date": "2024-01-01",
                "filing_date": "2023-01-01",
                "country": "US",
                "source_url": "https://example.test/us",
                "keywords": "fiber; sensor",
            },
            {
                "source": "EPO",
                "patent_id": "EP-LEGACY-CURRENT-1",
                "publication_number": "EP-LEGACY-CURRENT-1",
                "title": "Textile electrode system",
                "abstract": "A wearable textile electrode.",
                "assignee": "Weave Labs",
                "inventors": "Bora Example",
                "publication_date": "2024-02-01",
                "filing_date": "2023-02-01",
                "country": "EP",
                "source_url": "https://example.test/ep",
                "keywords": "textile; electrode",
            },
            {
                "source": "TURKPATENT",
                "patent_id": "TR-LEGACY-CURRENT-1",
                "publication_number": "TR-LEGACY-CURRENT-1",
                "title": "Movement tracking fabric",
                "abstract": "A smart garment for rehabilitation.",
                "assignee": "Rehab Textiles",
                "inventors": "Cem Example",
                "publication_date": "2024-03-01",
                "filing_date": "2023-03-01",
                "country": "TR",
                "source_url": "https://example.test/tr",
                "keywords": "movement; fabric",
            },
        ],
    )
    normalized_records, canonical_summary = service._prepare_prepared_source_dataset(
        service._canonical_corpus_path()
    )
    service.repository.upsert_patents(normalized_records)
    legacy_active = service.repository.get_active_corpus_version()
    before_patents = _patent_metadata_rows(service.repository.database_path)
    before_import_batch_count = _table_count(
        service.repository.database_path, "import_batches"
    )

    summary = service.ensure_canonical_corpus_loaded()

    active = _active_corpus_metadata(service.repository.database_path)
    stored_summary = json.loads(str(active["summary_json"]))
    assert legacy_active is not None
    assert legacy_active["dataset_kind"] == "legacy_sqlite"
    assert legacy_active["source_file_hash"] is None
    assert summary["sync_action"] == "skipped"
    assert summary["sync_reason"] == "already_current_metadata_refreshed"
    assert summary["metadata_action"] == "updated_canonical_metadata"
    assert summary["import_batch_id"] is None
    assert summary["upserted_rows"] == 0
    assert active["id"] == legacy_active["id"]
    assert active["corpus_hash"] == legacy_active["corpus_hash"]
    assert active["dataset_kind"] == "prepared_source"
    assert active["source_label"] == "EPO / USPTO / TURKPATENT"
    assert active["source_file_hash"] == summary["source_file_hash"]
    assert (
        json.loads(str(active["source_counts_json"]))
        == canonical_summary["source_counts"]
    )
    assert stored_summary["canonical_path"] == summary["canonical_path"]
    assert stored_summary["source_file_hash"] == summary["source_file_hash"]
    assert stored_summary["corpus_hash"] == summary["corpus_hash"]
    assert (
        _table_count(service.repository.database_path, "import_batches")
        == before_import_batch_count
    )
    assert _patent_metadata_rows(service.repository.database_path) == before_patents


def test_second_startup_after_metadata_refresh_is_plain_skip(tmp_path) -> None:
    service = _isolated_service(tmp_path)
    _write_canonical_source_csv(
        service.settings.storage.raw_data_dir,
        [
            {
                "source": "USPTO",
                "patent_id": "US-REFRESH-ONCE-1",
                "publication_number": "US-REFRESH-ONCE-1",
                "title": "Conductive yarn garment",
                "abstract": "A wearable textile sensor.",
                "assignee": "Fiber Labs",
                "inventors": "Ada Example",
                "publication_date": "2024-01-01",
                "filing_date": "2023-01-01",
                "country": "US",
                "source_url": "https://example.test/us",
                "keywords": "fiber; sensor",
            }
        ],
    )
    normalized_records, _summary = service._prepare_prepared_source_dataset(
        service._canonical_corpus_path()
    )
    service.repository.upsert_patents(normalized_records)

    first_summary = service.ensure_canonical_corpus_loaded()
    metadata_after_first = _active_corpus_metadata(service.repository.database_path)
    import_batch_count_after_first = _table_count(
        service.repository.database_path, "import_batches"
    )
    second_summary = service.ensure_canonical_corpus_loaded()

    assert first_summary["sync_reason"] == "already_current_metadata_refreshed"
    assert second_summary["sync_action"] == "skipped"
    assert second_summary["sync_reason"] == "already_current"
    assert second_summary["import_batch_id"] is None
    assert "metadata_action" not in second_summary
    assert (
        _table_count(service.repository.database_path, "import_batches")
        == import_batch_count_after_first
    )
    assert (
        _active_corpus_metadata(service.repository.database_path)
        == metadata_after_first
    )


def test_canonical_corpus_hash_is_stable_when_csv_rows_reorder(tmp_path) -> None:
    service = _isolated_service(tmp_path)
    rows = [
        {
            "source": "USPTO",
            "patent_id": "US-STABLE-1",
            "publication_number": "US-STABLE-1",
            "title": "Conductive yarn garment",
            "abstract": "A wearable textile sensor.",
            "assignee": "Fiber Labs",
            "inventors": "Ada Example",
            "publication_date": "2024-01-01",
            "filing_date": "2023-01-01",
            "country": "US",
            "source_url": "https://example.test/us",
            "keywords": "fiber; sensor",
        },
        {
            "source": "EPO",
            "patent_id": "EP-STABLE-1",
            "publication_number": "EP-STABLE-1",
            "title": "Textile electrode system",
            "abstract": "A wearable textile electrode.",
            "assignee": "Weave Labs",
            "inventors": "Bora Example",
            "publication_date": "2024-02-01",
            "filing_date": "2023-02-01",
            "country": "EP",
            "source_url": "https://example.test/ep",
            "keywords": "textile; electrode",
        },
    ]
    _write_canonical_source_csv(service.settings.storage.raw_data_dir, rows)
    first_summary = service.ensure_canonical_corpus_loaded()

    _write_canonical_source_csv(
        service.settings.storage.raw_data_dir, list(reversed(rows))
    )
    second_summary = service.ensure_canonical_corpus_loaded()

    assert second_summary["sync_action"] == "skipped"
    assert second_summary["corpus_hash"] == first_summary["corpus_hash"]


def test_canonical_corpus_hash_changes_when_normalized_row_changes(tmp_path) -> None:
    service = _isolated_service(tmp_path)
    row = {
        "source": "USPTO",
        "patent_id": "US-EDIT-1",
        "publication_number": "US-EDIT-1",
        "title": "Conductive yarn garment",
        "abstract": "A wearable textile sensor.",
        "assignee": "Fiber Labs",
        "inventors": "Ada Example",
        "publication_date": "2024-01-01",
        "filing_date": "2023-01-01",
        "country": "US",
        "source_url": "https://example.test/us",
        "keywords": "fiber; sensor",
    }
    _write_canonical_source_csv(service.settings.storage.raw_data_dir, [row])
    first_summary = service.ensure_canonical_corpus_loaded()
    edited_row = {**row, "title": "Updated conductive yarn garment"}

    _write_canonical_source_csv(service.settings.storage.raw_data_dir, [edited_row])
    second_summary = service.ensure_canonical_corpus_loaded()

    assert second_summary["sync_action"] == "reloaded_canonical_corpus"
    assert second_summary["sync_reason"] == "canonical_records_changed"
    assert second_summary["corpus_hash"] != first_summary["corpus_hash"]


def test_empty_prepared_source_template_imports_without_crashing(tmp_path) -> None:
    csv_path = tmp_path / "empty_prepared_sources.csv"
    csv_path.write_text(
        ",".join(CANONICAL_CORPUS_SCHEMA_COLUMNS) + "\n",
        encoding="utf-8",
    )
    service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )

    summary = service.import_prepared_source_dataset(csv_path)

    assert summary["dataset_kind"] == "prepared_source"
    assert summary["total_raw_rows"] == 0
    assert summary["valid_normalized_rows"] == 0
    assert summary["skipped_rows"] == 0
    assert summary["upserted_rows"] == 0
    assert summary["source_counts"] == {"EPO": 0, "USPTO": 0, "TURKPATENT": 0}
    assert "ready to be filled" in summary["message"]
    assert service.repository.count_patents() == 0


def test_corpus_quality_audit_flags_future_intake_review_reasons() -> None:
    row = {
        "source": "example-office",
        "patent_id": "US-TEST-1",
        "publication_number": "US-TEST-1",
        "title": "Fiber sensor",
        "abstract": "Wearable textile electronics.",
        "assignee": "Example Labs",
        "inventors": "Ada Example",
        "publication_date": "2026-01-01",
        "filing_date": "2025-01-01",
        "country": "US",
        "source_url": "N/A",
        "keywords": "fiber; sensor",
        "candidate_application_areas": "",
        "ipc_codes": "",
        "cpc_codes": "",
    }

    audit = audit_corpus_row(row)

    assert not audit.is_accepted
    assert "candidate_application_areas" in audit.missing_fields
    assert "source" in audit.invalid_fields
    assert "source_url" in audit.invalid_fields
    assert "missing both ipc_codes and cpc_codes" in audit.review_reasons


def test_prepared_source_dataset_missing_columns_raise_clear_error(tmp_path) -> None:
    csv_path = tmp_path / "missing_columns.csv"
    csv_path.write_text(
        "patent_id,source,title\n" "TEST-1,EPO,Test fiber record\n",
        encoding="utf-8",
    )
    service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )

    with pytest.raises(ValueError, match="missing required column"):
        service.import_prepared_source_dataset(csv_path)


def test_prepared_source_dataset_counts_source_labels(tmp_path) -> None:
    csv_path = tmp_path / "source_counts.csv"
    csv_path.write_text(
        ",".join(PREPARED_SOURCE_DATASET_REQUIRED_COLUMNS)
        + "\n"
        + "TEST-EPO-1,EPO,Fiber sensor,Curated test abstract,"
        + "Example Assignee,Ada Example,2026-01-01,2025-01-01,"
        + "EP,fiber; sensor,https://example.test/epo\n"
        + "TEST-USPTO-1,USPTO,Textile electrode,Curated test abstract,"
        + "Example Assignee,Bob Example,2026-01-02,2025-01-02,"
        + "US,textile; electrode,https://example.test/uspto\n"
        + "TEST-TPO-1,TPO,Conductive yarn,Curated test abstract,"
        + "Example Assignee,Cem Example,2026-01-03,2025-01-03,"
        + "TR,conductive; yarn,https://example.test/tpo\n",
        encoding="utf-8",
    )
    service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )

    summary = service.import_prepared_source_dataset(csv_path)

    assert summary["source"] == "EPO / USPTO / TURKPATENT"
    assert summary["total_raw_rows"] == 3
    assert summary["valid_normalized_rows"] == 3
    assert summary["skipped_rows"] == 0
    assert summary["upserted_rows"] == 3
    assert summary["source_counts"] == {"EPO": 1, "USPTO": 1, "TURKPATENT": 1}
    assert {record.source for record in service.repository.fetch_all_patents()} == {
        SourceType.EPO,
        SourceType.USPTO,
        SourceType.TURKPATENT,
    }


def test_standard_csv_import_still_uses_csv_import_source(tmp_path) -> None:
    csv_path = tmp_path / "manual_patents.csv"
    csv_path.write_text(
        "patent_id,source,title,abstract\n"
        "TEST-CSV-1,EPO,Manual CSV row,Manual import abstract\n",
        encoding="utf-8",
    )
    service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )

    summary = service.import_patents(csv_path)

    assert summary["source"] == SourceType.CSV_IMPORT.value
    assert summary["valid_normalized_rows"] == 1
    assert service.repository.fetch_all_patents()[0].source is SourceType.CSV_IMPORT


def test_pipeline_imports_json_happy_path(tmp_path) -> None:
    json_path = tmp_path / "patents.json"
    json_path.write_text(
        """
        {
          "records": [
            {
              "id": "JP-1",
              "title": "Conductive textile",
              "abstract": "A conductive fiber textile.",
              "keywords": ["fiber", "textile"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )

    summary = service.import_patents(json_path)

    assert summary["source"] == SourceType.JSON_IMPORT.value
    assert summary["total_raw_rows"] == 1
    assert summary["valid_normalized_rows"] == 1
    assert summary["skipped_rows"] == 0
    assert summary["upserted_rows"] == 1

    saved_record = service.repository.fetch_all_patents()[0]
    assert saved_record.patent_id == "JP-1"
    assert saved_record.source is SourceType.JSON_IMPORT
    assert saved_record.keywords == ["fiber", "textile"]


def test_manual_import_writes_row_hash_and_batch_without_activating_corpus(
    tmp_path,
) -> None:
    csv_path = tmp_path / "manual_patents.csv"
    csv_path.write_text(
        "patent_id,title,abstract,inventors,ipc_codes\n"
        "US-MANUAL-1,Fiber sensor,Wearable electronics,Ada Example,A61B\n",
        encoding="utf-8",
    )
    service = PipelineService(
        settings=AppSettings(),
        repository=SQLiteRepository(tmp_path / "patents.sqlite3"),
    )

    summary = service.import_patents(csv_path)

    with sqlite3.connect(service.repository.database_path) as connection:
        row = connection.execute("""
            SELECT import_batch_id, corpus_version_id, row_hash
            FROM patents
            WHERE patent_id = 'US-MANUAL-1'
            """).fetchone()
        active_corpus_count = connection.execute("""
            SELECT COUNT(*)
            FROM corpus_versions
            WHERE is_active = 1
            """).fetchone()[0]

    assert summary["dataset_kind"] == "manual_import"
    assert summary["import_batch_id"] is not None
    assert row[0] == summary["import_batch_id"]
    assert row[1] is None
    assert row[2]
    assert active_corpus_count == 0
