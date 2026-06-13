"""Tests for SQLite scaffold initialization."""

import sqlite3

from src.models.enums import SourceType
from src.models.patent import PatentRecord
from src.storage.sqlite_repository import SQLiteRepository


def _sample_record(
    patent_id: str = "US-TEST-1",
    *,
    source: SourceType = SourceType.CSV_IMPORT,
    title: str = "Fiber sensor",
    abstract: str = "Wearable electronics.",
) -> PatentRecord:
    return PatentRecord(
        patent_id=patent_id,
        source=source,
        title=title,
        abstract=abstract,
        publication_number=f"{patent_id}-PUB",
        claims_text="A claim.",
        claims_excerpt="A claim excerpt.",
        assignee="Example Labs",
        inventors=["Ada Example"],
        ipc_codes=["A61B"],
        cpc_codes=["H01B"],
        keywords=["fiber", "wearable"],
        candidate_application_areas=["Healthcare monitoring", "Smart garments"],
        patent_family="123456",
        citation_count=17,
    )


def test_sqlite_repository_initializes_expected_tables(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)

    repository.initialize()

    assert database_path.exists()

    with sqlite3.connect(database_path) as connection:
        table_rows = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """).fetchall()

    table_names = {row[0] for row in table_rows}
    assert {
        "analysis_runs",
        "corpus_versions",
        "import_batches",
        "patents",
        "patent_keywords",
        "patent_classifications",
        "patent_application_areas",
        "patent_quality_flags",
    }.issubset(table_names)


def test_sqlite_repository_initializes_v2_import_and_corpus_columns(
    tmp_path,
) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)

    repository.initialize()

    with sqlite3.connect(database_path) as connection:
        corpus_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(corpus_versions)")
        }
        import_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(import_batches)")
        }
        patent_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(patents)")
        }

    assert {
        "version_label",
        "corpus_hash",
        "dataset_kind",
        "source_label",
        "source_file_hash",
        "source_counts_json",
        "summary_json",
        "is_active",
        "activated_at",
        "created_from_import_batch_id",
        "hash_algorithm",
        "row_hash_version",
        "row_hash",
    }.issubset(corpus_columns)
    assert {
        "workflow",
        "dataset_kind",
        "source_file_hash",
        "corpus_hash",
        "status",
        "total_raw_rows",
        "valid_normalized_rows",
        "skipped_rows",
        "upserted_rows",
        "inserted_rows",
        "updated_rows",
        "unchanged_rows",
        "summary_json",
        "error_message",
        "started_at",
        "completed_at",
    }.issubset(import_columns)
    assert "idx_patents_row_hash" in patent_indexes


def test_patents_table_contains_canonical_placeholder_columns(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)
    repository.initialize()

    with sqlite3.connect(database_path) as connection:
        columns = connection.execute("PRAGMA table_info(patents)").fetchall()

        column_names = {column[1] for column in columns}
        assert {
            "id",
            "patent_id",
            "analysis_id",
            "publication_number",
            "source",
            "title",
            "abstract",
            "claims_text",
            "claims_excerpt",
            "description_text",
            "assignee",
            "inventors",
            "publication_date",
            "filing_date",
            "ipc_codes",
            "cpc_codes",
            "country",
            "language",
            "source_url",
            "keywords",
            "candidate_application_areas",
            "patent_family",
            "citation_count",
            "raw_source_ref",
            "import_batch_id",
            "corpus_version_id",
            "row_hash",
            "created_at",
            "updated_at",
        }.issubset(column_names)

        id_column = next(column for column in columns if column[1] == "id")
        assert id_column[5] == 1

        unique_indexes = connection.execute("PRAGMA index_list(patents)").fetchall()
        has_patent_source_unique_index = False
        for index in unique_indexes:
            if not index[2]:
                continue

            indexed_columns = connection.execute(
                f"PRAGMA index_info({index[1]})"
            ).fetchall()
            indexed_column_names = [column[2] for column in indexed_columns]
            if indexed_column_names == ["patent_id", "source"]:
                has_patent_source_unique_index = True

        assert has_patent_source_unique_index


def test_sqlite_repository_upserts_fetches_counts_and_clears_patents(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)
    record = _sample_record()

    upserted_rows = repository.upsert_patents([record])

    assert upserted_rows == 1
    assert repository.count_patents() == 1

    saved_records = repository.fetch_all_patents()
    assert len(saved_records) == 1
    assert saved_records[0].patent_id == "US-TEST-1"
    assert saved_records[0].publication_number == "US-TEST-1-PUB"
    assert saved_records[0].claims_excerpt == "A claim excerpt."
    assert saved_records[0].inventors == ["Ada Example"]
    assert saved_records[0].ipc_codes == ["A61B"]
    assert saved_records[0].keywords == ["fiber", "wearable"]
    assert saved_records[0].candidate_application_areas == [
        "Healthcare monitoring",
        "Smart garments",
    ]
    assert saved_records[0].patent_family == "123456"
    assert saved_records[0].citation_count == 17

    repository.clear_patents()

    assert repository.count_patents() == 0


def test_import_batch_lifecycle_methods(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)

    completed_id = repository.create_import_batch(
        workflow="manual_import",
        dataset_kind="manual_import",
        source_label="CSV_IMPORT",
        total_raw_rows=2,
        valid_normalized_rows=1,
        skipped_rows=1,
    )
    completed = repository.complete_import_batch(
        completed_id,
        upserted_rows=1,
        inserted_rows=1,
        updated_rows=0,
        unchanged_rows=0,
    )
    skipped_id = repository.create_import_batch(
        workflow="load_prepared",
        dataset_kind="prepared_source",
        source_label="prepared",
    )
    skipped = repository.skip_import_batch(skipped_id, valid_normalized_rows=3)
    failed_id = repository.create_import_batch(
        workflow="startup_sync",
        dataset_kind="canonical_corpus",
        source_label="canonical",
    )
    failed = repository.fail_import_batch(failed_id, error_message="boom")

    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None
    assert completed["upserted_rows"] == 1
    assert skipped["status"] == "skipped"
    assert skipped["unchanged_rows"] == 3
    assert failed["status"] == "failed"
    assert failed["error_message"] == "boom"


def test_get_or_create_corpus_version_is_idempotent_by_hash(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)

    first = repository.get_or_create_corpus_version(
        corpus_hash="abc123",
        dataset_kind="prepared_source",
        source_label="prepared",
        row_count=2,
    )
    second = repository.get_or_create_corpus_version(
        corpus_hash="abc123",
        dataset_kind="prepared_source",
        source_label="prepared changed",
        row_count=3,
    )

    assert first["id"] == second["id"]
    assert first["corpus_hash"] == "abc123"


def test_activate_corpus_version_leaves_only_one_active(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)
    first = repository.create_corpus_version(
        corpus_hash="hash-one",
        dataset_kind="prepared_source",
        source_label="prepared",
    )
    second = repository.create_corpus_version(
        corpus_hash="hash-two",
        dataset_kind="prepared_source",
        source_label="prepared",
    )

    repository.activate_corpus_version(int(first["id"]))
    active = repository.activate_corpus_version(int(second["id"]))

    with sqlite3.connect(database_path) as connection:
        active_count = connection.execute(
            "SELECT COUNT(*) FROM corpus_versions WHERE is_active = 1"
        ).fetchone()[0]

    assert active["id"] == second["id"]
    assert active_count == 1


def test_upsert_patents_with_import_metadata_writes_version_fields(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)
    record = _sample_record()
    row_hashes = repository.row_hashes_for_records([record])
    import_batch_id = repository.create_import_batch(
        workflow="startup_sync",
        dataset_kind="canonical_corpus",
        source_label="canonical",
    )
    corpus_version = repository.create_corpus_version(
        corpus_hash=repository.corpus_hash_for_row_hashes(row_hashes),
        dataset_kind="canonical_corpus",
        source_label="canonical",
    )

    counts = repository.upsert_patents_with_import_metadata(
        [record],
        row_hashes,
        import_batch_id,
        int(corpus_version["id"]),
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT import_batch_id, corpus_version_id, row_hash
            FROM patents
            WHERE patent_id = ?
            """,
            (record.patent_id,),
        ).fetchone()

    assert counts == {
        "upserted_rows": 1,
        "inserted_rows": 1,
        "updated_rows": 0,
        "unchanged_rows": 0,
    }
    assert row[0] == import_batch_id
    assert row[1] == corpus_version["id"]
    assert row[2] == row_hashes[record.analysis_id]


def test_replace_patents_for_corpus_prunes_stale_rows(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)
    stale_record = _sample_record("US-STALE-1")
    fresh_record = _sample_record("US-FRESH-1")
    repository.upsert_patents([stale_record])
    row_hashes = repository.row_hashes_for_records([fresh_record])
    import_batch_id = repository.create_import_batch(
        workflow="startup_sync",
        dataset_kind="canonical_corpus",
        source_label="canonical",
    )
    corpus_version = repository.create_corpus_version(
        corpus_hash=repository.corpus_hash_for_row_hashes(row_hashes),
        dataset_kind="canonical_corpus",
        source_label="canonical",
    )

    counts = repository.replace_patents_for_corpus(
        [fresh_record],
        row_hashes,
        import_batch_id,
        int(corpus_version["id"]),
    )

    saved_records = repository.fetch_all_patents()
    assert counts["upserted_rows"] == 1
    assert counts["pruned_rows"] == 1
    assert [record.patent_id for record in saved_records] == ["US-FRESH-1"]


def test_unchanged_row_hash_is_counted_as_unchanged(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)
    record = _sample_record()
    row_hashes = repository.row_hashes_for_records([record])
    corpus_version = repository.create_corpus_version(
        corpus_hash=repository.corpus_hash_for_row_hashes(row_hashes),
        dataset_kind="canonical_corpus",
        source_label="canonical",
    )
    first_batch_id = repository.create_import_batch(
        workflow="startup_sync",
        dataset_kind="canonical_corpus",
        source_label="canonical",
    )
    second_batch_id = repository.create_import_batch(
        workflow="startup_sync",
        dataset_kind="canonical_corpus",
        source_label="canonical",
    )
    repository.upsert_patents_with_import_metadata(
        [record],
        row_hashes,
        first_batch_id,
        int(corpus_version["id"]),
    )

    counts = repository.upsert_patents_with_import_metadata(
        [record],
        row_hashes,
        second_batch_id,
        int(corpus_version["id"]),
    )

    assert counts["unchanged_rows"] == 1
    assert counts["inserted_rows"] == 0
    assert counts["updated_rows"] == 0


def test_migration_backfill_versions_existing_unversioned_patents(tmp_path) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)

    repository.upsert_patents([_sample_record("US-LEGACY-1")])
    hash_index = repository.fetch_patent_hash_index()
    active_version = repository.get_active_corpus_version()

    with sqlite3.connect(database_path) as connection:
        patent_row = connection.execute("""
            SELECT import_batch_id, corpus_version_id, row_hash
            FROM patents
            WHERE patent_id = 'US-LEGACY-1'
            """).fetchone()
        backfill_batch_count = connection.execute("""
            SELECT COUNT(*)
            FROM import_batches
            WHERE workflow = 'migration_backfill' AND status = 'completed'
            """).fetchone()[0]

    assert hash_index["CSV_IMPORT:US-LEGACY-1"]
    assert active_version is not None
    assert active_version["version_label"].startswith("legacy-sqlite-")
    assert patent_row[0] is not None
    assert patent_row[1] == active_version["id"]
    assert patent_row[2] == hash_index["CSV_IMPORT:US-LEGACY-1"]
    assert backfill_batch_count == 1


def test_sqlite_repository_upserts_same_patent_and_source_without_extra_row(
    tmp_path,
) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)
    original_record = PatentRecord(
        patent_id="US-DUP-1",
        source=SourceType.CSV_IMPORT,
        title="Original title",
        abstract="Original abstract.",
    )
    updated_record = PatentRecord(
        patent_id="US-DUP-1",
        source=SourceType.CSV_IMPORT,
        title="Updated title",
        abstract="Updated abstract.",
    )

    assert repository.upsert_patents([original_record]) == 1
    assert repository.upsert_patents([updated_record]) == 1

    saved_records = repository.fetch_all_patents()
    assert repository.count_patents() == 1
    assert len(saved_records) == 1
    assert saved_records[0].title == "Updated title"
    assert saved_records[0].abstract == "Updated abstract."


def test_sqlite_repository_keeps_same_patent_id_from_different_sources(
    tmp_path,
) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    repository = SQLiteRepository(database_path)
    csv_record = PatentRecord(
        patent_id="SHARED-1",
        source=SourceType.CSV_IMPORT,
        title="CSV title",
        abstract="CSV abstract.",
    )
    json_record = PatentRecord(
        patent_id="SHARED-1",
        source=SourceType.JSON_IMPORT,
        title="JSON title",
        abstract="JSON abstract.",
    )

    assert repository.upsert_patents([csv_record, json_record]) == 2

    saved_records = repository.fetch_all_patents()
    assert repository.count_patents() == 2
    assert {record.source for record in saved_records} == {
        SourceType.CSV_IMPORT,
        SourceType.JSON_IMPORT,
    }


def test_sqlite_repository_migrates_existing_v1_patents_without_losing_rows(
    tmp_path,
) -> None:
    database_path = tmp_path / "patent_analysis.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TABLE patents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patent_id TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT NOT NULL,
                claims_text TEXT,
                description_text TEXT,
                assignee TEXT,
                inventors TEXT NOT NULL DEFAULT '[]',
                publication_date TEXT,
                filing_date TEXT,
                ipc_codes TEXT NOT NULL DEFAULT '[]',
                cpc_codes TEXT NOT NULL DEFAULT '[]',
                country TEXT,
                language TEXT,
                source_url TEXT,
                keywords TEXT NOT NULL DEFAULT '[]',
                raw_source_ref TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patent_id, source)
            )
            """)
        connection.execute(
            """
            INSERT INTO patents (
                patent_id,
                source,
                title,
                abstract,
                claims_text,
                inventors,
                ipc_codes,
                cpc_codes,
                keywords
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "US-V1-1",
                SourceType.CSV_IMPORT.value,
                "Legacy row",
                "Legacy abstract.",
                "Legacy claim.",
                '["Ada Example"]',
                '["A61B"]',
                '["H01B"]',
                '["fiber"]',
            ),
        )
        connection.commit()

    repository = SQLiteRepository(database_path)
    repository.initialize()

    saved_records = repository.fetch_all_patents()
    assert repository.count_patents() == 1
    assert len(saved_records) == 1
    assert saved_records[0].patent_id == "US-V1-1"
    assert saved_records[0].publication_number == "US-V1-1"
    assert saved_records[0].claims_excerpt == "Legacy claim."
    assert saved_records[0].candidate_application_areas == []
