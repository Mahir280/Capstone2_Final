"""Direct sqlite3 repository for local patent storage."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.models.enums import SourceType
from src.models.patent import PatentRecord


class SQLiteRepository:
    """Store canonical patent records in a local SQLite database."""

    HASH_ALGORITHM = "sha256"
    ROW_HASH_VERSION = "normalized-patent-v1"
    _ROW_HASH_FIELDS = (
        "source",
        "patent_id",
        "publication_number",
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
    )
    _PATENT_UPSERT_COLUMNS = (
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
    )
    _PATENT_FETCH_COLUMNS = _PATENT_UPSERT_COLUMNS
    _PATENT_COPY_COLUMNS = (
        *_PATENT_UPSERT_COLUMNS,
        "import_batch_id",
        "corpus_version_id",
        "row_hash",
        "created_at",
        "updated_at",
    )
    _PATENT_ADD_COLUMN_SQL = {
        "analysis_id": "analysis_id TEXT",
        "publication_number": "publication_number TEXT",
        "claims_excerpt": "claims_excerpt TEXT",
        "candidate_application_areas": (
            "candidate_application_areas TEXT NOT NULL DEFAULT '[]'"
        ),
        "patent_family": "patent_family TEXT",
        "citation_count": "citation_count INTEGER",
        "import_batch_id": "import_batch_id INTEGER",
        "corpus_version_id": "corpus_version_id INTEGER",
        "row_hash": "row_hash TEXT",
        "updated_at": "updated_at TEXT",
    }

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        """Open a SQLite connection with row access by column name."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        """Create scaffold tables if they do not already exist."""
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    source_label TEXT NOT NULL,
                    record_count INTEGER NOT NULL,
                    notes TEXT
                )
                """)
            self._ensure_foundation_tables(connection)
            self._ensure_patents_table(connection)
            self._backfill_patent_versioning_state(connection)
            connection.commit()

    def upsert_patents(self, records: Iterable[PatentRecord]) -> int:
        """Insert or update normalized patent records and return handled rows."""
        record_list = list(records)
        if not record_list:
            return 0

        self.initialize()
        upserted_rows = 0
        columns_sql = ",\n                        ".join(self._PATENT_UPSERT_COLUMNS)
        placeholders_sql = ", ".join("?" for _ in self._PATENT_UPSERT_COLUMNS)
        update_columns = [
            column
            for column in self._PATENT_UPSERT_COLUMNS
            if column not in {"patent_id", "source"}
        ]
        updates_sql = ",\n                        ".join(
            f"{column} = excluded.{column}" for column in update_columns
        )
        with self.connect() as connection:
            for record in record_list:
                connection.execute(
                    f"""
                    INSERT INTO patents (
                        {columns_sql}
                    )
                    VALUES ({placeholders_sql})
                    ON CONFLICT(patent_id, source) DO UPDATE SET
                        {updates_sql},
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    self._record_to_row(record),
                )
                upserted_rows += 1

            connection.commit()

        return upserted_rows

    def fetch_all_patents(self) -> list[PatentRecord]:
        """Fetch all saved patents as canonical records."""
        self.initialize()
        columns_sql = ",\n                    ".join(self._PATENT_FETCH_COLUMNS)
        with self.connect() as connection:
            rows = connection.execute(f"""
                SELECT
                    {columns_sql}
                FROM patents
                ORDER BY created_at DESC, id DESC, patent_id ASC
                """).fetchall()

        return [self._row_to_record(row) for row in rows]

    def count_patents(self) -> int:
        """Return the number of saved patent rows."""
        self.initialize()
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM patents").fetchone()

        return int(row["count"])

    def clear_patents(self) -> None:
        """Remove all saved patents, mainly for isolated tests."""
        self.initialize()
        with self.connect() as connection:
            connection.execute("DELETE FROM patents")
            connection.commit()

    def create_import_batch(
        self,
        *,
        workflow: str,
        dataset_kind: str,
        source_label: str,
        source_path: str | None = None,
        source_file_hash: str | None = None,
        corpus_hash: str | None = None,
        status: str = "created",
        total_raw_rows: int = 0,
        valid_normalized_rows: int = 0,
        skipped_rows: int = 0,
        summary: dict[str, Any] | None = None,
    ) -> int:
        """Create an auditable import batch and return its id."""
        self.initialize()
        with self.connect() as connection:
            import_batch_id = self._create_import_batch(
                connection,
                workflow=workflow,
                dataset_kind=dataset_kind,
                source_label=source_label,
                source_path=source_path,
                source_file_hash=source_file_hash,
                corpus_hash=corpus_hash,
                status=status,
                total_raw_rows=total_raw_rows,
                valid_normalized_rows=valid_normalized_rows,
                skipped_rows=skipped_rows,
                summary=summary,
            )
            connection.commit()
            return import_batch_id

    def complete_import_batch(
        self,
        import_batch_id: int,
        *,
        corpus_version_id: int | None = None,
        total_raw_rows: int | None = None,
        valid_normalized_rows: int | None = None,
        skipped_rows: int | None = None,
        upserted_rows: int | None = None,
        inserted_rows: int | None = None,
        updated_rows: int | None = None,
        unchanged_rows: int | None = None,
        summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mark an import batch completed and return the saved row."""
        with self.connect() as connection:
            self._update_import_batch(
                connection,
                import_batch_id,
                status="completed",
                corpus_version_id=corpus_version_id,
                total_raw_rows=total_raw_rows,
                valid_normalized_rows=valid_normalized_rows,
                skipped_rows=skipped_rows,
                upserted_rows=upserted_rows,
                inserted_rows=inserted_rows,
                updated_rows=updated_rows,
                unchanged_rows=unchanged_rows,
                summary=summary,
                completed=True,
            )
            connection.commit()
            return self._get_import_batch(connection, import_batch_id)

    def skip_import_batch(
        self,
        import_batch_id: int,
        *,
        corpus_version_id: int | None = None,
        total_raw_rows: int | None = None,
        valid_normalized_rows: int | None = None,
        skipped_rows: int | None = None,
        summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mark an import batch as an intentional idempotent skip."""
        with self.connect() as connection:
            self._update_import_batch(
                connection,
                import_batch_id,
                status="skipped",
                corpus_version_id=corpus_version_id,
                total_raw_rows=total_raw_rows,
                valid_normalized_rows=valid_normalized_rows,
                skipped_rows=skipped_rows,
                upserted_rows=0,
                inserted_rows=0,
                updated_rows=0,
                unchanged_rows=valid_normalized_rows,
                summary=summary,
                completed=True,
            )
            connection.commit()
            return self._get_import_batch(connection, import_batch_id)

    def fail_import_batch(
        self,
        import_batch_id: int,
        *,
        error_message: str,
        summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mark an import batch failed and return the saved row."""
        with self.connect() as connection:
            self._update_import_batch(
                connection,
                import_batch_id,
                status="failed",
                summary=summary,
                error_message=error_message,
                completed=True,
            )
            connection.commit()
            return self._get_import_batch(connection, import_batch_id)

    def get_corpus_version_by_hash(self, corpus_hash: str) -> dict[str, Any] | None:
        """Return a corpus version by deterministic corpus hash."""
        self.initialize()
        with self.connect() as connection:
            return self._get_corpus_version_by_hash(connection, corpus_hash)

    def create_corpus_version(
        self,
        *,
        corpus_hash: str,
        dataset_kind: str,
        source_label: str,
        label: str | None = None,
        source_path: str | None = None,
        source_file_hash: str | None = None,
        source_counts: dict[str, int] | None = None,
        summary: dict[str, Any] | None = None,
        row_count: int = 0,
        created_from_import_batch_id: int | None = None,
    ) -> dict[str, Any]:
        """Create a corpus version row, or return the existing hash match."""
        self.initialize()
        with self.connect() as connection:
            corpus_version = self._create_corpus_version(
                connection,
                corpus_hash=corpus_hash,
                dataset_kind=dataset_kind,
                source_label=source_label,
                label=label,
                source_path=source_path,
                source_file_hash=source_file_hash,
                source_counts=source_counts,
                summary=summary,
                row_count=row_count,
                created_from_import_batch_id=created_from_import_batch_id,
            )
            connection.commit()
            return corpus_version

    def get_or_create_corpus_version(
        self,
        *,
        corpus_hash: str,
        dataset_kind: str,
        source_label: str,
        label: str | None = None,
        source_path: str | None = None,
        source_file_hash: str | None = None,
        source_counts: dict[str, int] | None = None,
        summary: dict[str, Any] | None = None,
        row_count: int = 0,
        created_from_import_batch_id: int | None = None,
    ) -> dict[str, Any]:
        """Return the existing corpus version for a hash, creating it if needed."""
        self.initialize()
        with self.connect() as connection:
            corpus_version = self._get_or_create_corpus_version(
                connection,
                corpus_hash=corpus_hash,
                dataset_kind=dataset_kind,
                source_label=source_label,
                label=label,
                source_path=source_path,
                source_file_hash=source_file_hash,
                source_counts=source_counts,
                summary=summary,
                row_count=row_count,
                created_from_import_batch_id=created_from_import_batch_id,
            )
            connection.commit()
            return corpus_version

    def update_corpus_version_metadata(
        self,
        corpus_version_id: int,
        *,
        dataset_kind: str,
        source_label: str,
        source_path: str | None = None,
        source_file_hash: str | None = None,
        source_counts: dict[str, int] | None = None,
        summary: dict[str, Any] | None = None,
        row_count: int | None = None,
    ) -> dict[str, Any]:
        """Update audit metadata for an existing corpus version."""
        self.initialize()
        with self.connect() as connection:
            values: list[Any] = [
                dataset_kind,
                source_label,
                source_path,
                source_file_hash,
                self._dumps_json(source_counts or {}),
                self._dumps_json(summary or {}),
                self.HASH_ALGORITHM,
                self.ROW_HASH_VERSION,
            ]
            row_count_sql = ""
            if row_count is not None:
                row_count_sql = ", row_count = ?"
                values.append(row_count)
            values.append(corpus_version_id)
            connection.execute(
                f"""
                UPDATE corpus_versions
                SET dataset_kind = ?,
                    source_label = ?,
                    source_path = ?,
                    source_file_hash = ?,
                    source_counts_json = ?,
                    summary_json = ?,
                    hash_algorithm = ?,
                    row_hash_version = ?
                    {row_count_sql}
                WHERE id = ?
                """,
                tuple(values),
            )
            connection.commit()
            return self._get_corpus_version(connection, corpus_version_id)

    def activate_corpus_version(self, corpus_version_id: int) -> dict[str, Any]:
        """Mark one corpus version active and all others inactive."""
        self.initialize()
        with self.connect() as connection:
            corpus_version = self._activate_corpus_version(
                connection, corpus_version_id
            )
            connection.commit()
            return corpus_version

    def get_active_corpus_version(self) -> dict[str, Any] | None:
        """Return the currently active corpus version, if one exists."""
        self.initialize()
        with self.connect() as connection:
            return self._get_active_corpus_version(connection)

    def fetch_patent_hash_index(self) -> dict[str, str | None]:
        """Return current patent row hashes keyed by analysis id."""
        self.initialize()
        with self.connect() as connection:
            return self._fetch_patent_hash_index(connection)

    def upsert_patents_with_import_metadata(
        self,
        records: Iterable[PatentRecord],
        row_hashes: dict[str, str],
        import_batch_id: int,
        corpus_version_id: int | None,
    ) -> dict[str, int]:
        """Upsert patents while writing row/import/corpus version metadata."""
        record_list = list(records)
        if not record_list:
            return {
                "upserted_rows": 0,
                "inserted_rows": 0,
                "updated_rows": 0,
                "unchanged_rows": 0,
            }

        self.initialize()
        with self.connect() as connection:
            counts = self._upsert_patents_with_import_metadata(
                connection,
                record_list,
                row_hashes,
                import_batch_id,
                corpus_version_id,
            )
            connection.commit()
            return counts

    def replace_patents_for_corpus(
        self,
        records: Iterable[PatentRecord],
        row_hashes: dict[str, str],
        import_batch_id: int,
        corpus_version_id: int,
    ) -> dict[str, int]:
        """Replace the saved corpus with records for a versioned corpus import."""
        record_list = list(records)
        self.initialize()
        with self.connect() as connection:
            counts = self._upsert_patents_with_import_metadata(
                connection,
                record_list,
                row_hashes,
                import_batch_id,
                corpus_version_id,
            )
            expected_analysis_ids = {record.analysis_id for record in record_list}
            pruned_rows = self._prune_patents_not_in_corpus(
                connection, expected_analysis_ids
            )
            counts["deleted_rows"] = pruned_rows
            counts["pruned_rows"] = pruned_rows
            connection.commit()
            return counts

    @classmethod
    def row_hash_for_record(cls, record: PatentRecord) -> str:
        """Compute the deterministic v1 hash for a normalized patent record."""
        payload = cls._row_hash_payload(record)
        return cls._sha256_json(payload)

    @classmethod
    def row_hashes_for_records(cls, records: Iterable[PatentRecord]) -> dict[str, str]:
        """Compute row hashes keyed by analysis id."""
        return {
            record.analysis_id: cls.row_hash_for_record(record) for record in records
        }

    @classmethod
    def corpus_hash_for_row_hashes(cls, row_hashes: dict[str, str]) -> str:
        """Compute the deterministic corpus hash from row hashes."""
        payload = {
            "row_hash_version": cls.ROW_HASH_VERSION,
            "rows": sorted(row_hashes.items(), key=lambda item: item[0]),
        }
        return cls._sha256_json(payload)

    def _ensure_foundation_tables(self, connection: sqlite3.Connection) -> None:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS corpus_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_label TEXT NOT NULL UNIQUE,
                corpus_hash TEXT,
                dataset_kind TEXT,
                source_label TEXT,
                source_path TEXT,
                source_file_hash TEXT,
                source_counts_json TEXT NOT NULL DEFAULT '{}',
                summary_json TEXT NOT NULL DEFAULT '{}',
                is_active INTEGER NOT NULL DEFAULT 0,
                activated_at TEXT,
                created_from_import_batch_id INTEGER,
                hash_algorithm TEXT NOT NULL DEFAULT 'sha256',
                row_hash_version TEXT NOT NULL DEFAULT 'normalized-patent-v1',
                row_count INTEGER NOT NULL DEFAULT 0,
                row_hash TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                corpus_version_id INTEGER,
                workflow TEXT,
                dataset_kind TEXT,
                import_type TEXT NOT NULL,
                source_label TEXT,
                source_path TEXT,
                source_file_hash TEXT,
                corpus_hash TEXT,
                total_raw_rows INTEGER NOT NULL DEFAULT 0,
                valid_normalized_rows INTEGER NOT NULL DEFAULT 0,
                skipped_rows INTEGER NOT NULL DEFAULT 0,
                upserted_rows INTEGER NOT NULL DEFAULT 0,
                inserted_rows INTEGER NOT NULL DEFAULT 0,
                updated_rows INTEGER NOT NULL DEFAULT 0,
                unchanged_rows INTEGER NOT NULL DEFAULT 0,
                summary_json TEXT NOT NULL DEFAULT '{}',
                error_message TEXT,
                record_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'created',
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                notes TEXT,
                FOREIGN KEY(corpus_version_id) REFERENCES corpus_versions(id)
            )
            """)
        self._add_missing_foundation_columns(connection)
        self._backfill_foundation_table_columns(connection)
        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_corpus_versions_corpus_hash
            ON corpus_versions(corpus_hash)
            WHERE corpus_hash IS NOT NULL
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_corpus_versions_active
            ON corpus_versions(is_active)
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS patent_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patent_id TEXT NOT NULL,
                source TEXT NOT NULL,
                keyword TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patent_id, source, keyword)
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS patent_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patent_id TEXT NOT NULL,
                source TEXT NOT NULL,
                classification_system TEXT NOT NULL,
                classification_code TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(
                    patent_id,
                    source,
                    classification_system,
                    classification_code
                )
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS patent_application_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patent_id TEXT NOT NULL,
                source TEXT NOT NULL,
                application_area TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patent_id, source, application_area)
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS patent_quality_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patent_id TEXT NOT NULL,
                source TEXT NOT NULL,
                flag_type TEXT NOT NULL,
                flag_value TEXT,
                severity TEXT NOT NULL DEFAULT 'info',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                notes TEXT
            )
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_import_batches_corpus_version
            ON import_batches(corpus_version_id)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_import_batches_corpus_hash
            ON import_batches(corpus_hash)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_import_batches_workflow
            ON import_batches(workflow, status)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_patent_keywords_patent
            ON patent_keywords(patent_id, source)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_patent_classifications_patent
            ON patent_classifications(patent_id, source)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_patent_application_areas_patent
            ON patent_application_areas(patent_id, source)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_patent_quality_flags_patent
            ON patent_quality_flags(patent_id, source)
            """)

    def _add_missing_foundation_columns(self, connection: sqlite3.Connection) -> None:
        corpus_columns = self._table_column_names(connection, "corpus_versions")
        corpus_column_sql = {
            "corpus_hash": "corpus_hash TEXT",
            "dataset_kind": "dataset_kind TEXT",
            "source_label": "source_label TEXT",
            "source_path": "source_path TEXT",
            "source_file_hash": "source_file_hash TEXT",
            "source_counts_json": "source_counts_json TEXT NOT NULL DEFAULT '{}'",
            "summary_json": "summary_json TEXT NOT NULL DEFAULT '{}'",
            "is_active": "is_active INTEGER NOT NULL DEFAULT 0",
            "activated_at": "activated_at TEXT",
            "created_from_import_batch_id": "created_from_import_batch_id INTEGER",
            "hash_algorithm": "hash_algorithm TEXT NOT NULL DEFAULT 'sha256'",
            "row_hash_version": (
                "row_hash_version TEXT NOT NULL DEFAULT 'normalized-patent-v1'"
            ),
        }
        for column_name, column_sql in corpus_column_sql.items():
            if column_name not in corpus_columns:
                connection.execute(
                    f"ALTER TABLE corpus_versions ADD COLUMN {column_sql}"
                )

        import_columns = self._table_column_names(connection, "import_batches")
        import_column_sql = {
            "workflow": "workflow TEXT",
            "dataset_kind": "dataset_kind TEXT",
            "source_file_hash": "source_file_hash TEXT",
            "corpus_hash": "corpus_hash TEXT",
            "total_raw_rows": "total_raw_rows INTEGER NOT NULL DEFAULT 0",
            "valid_normalized_rows": (
                "valid_normalized_rows INTEGER NOT NULL DEFAULT 0"
            ),
            "skipped_rows": "skipped_rows INTEGER NOT NULL DEFAULT 0",
            "upserted_rows": "upserted_rows INTEGER NOT NULL DEFAULT 0",
            "inserted_rows": "inserted_rows INTEGER NOT NULL DEFAULT 0",
            "updated_rows": "updated_rows INTEGER NOT NULL DEFAULT 0",
            "unchanged_rows": "unchanged_rows INTEGER NOT NULL DEFAULT 0",
            "summary_json": "summary_json TEXT NOT NULL DEFAULT '{}'",
            "error_message": "error_message TEXT",
            "started_at": "started_at TEXT",
        }
        for column_name, column_sql in import_column_sql.items():
            if column_name not in import_columns:
                connection.execute(
                    f"ALTER TABLE import_batches ADD COLUMN {column_sql}"
                )

    def _backfill_foundation_table_columns(
        self, connection: sqlite3.Connection
    ) -> None:
        connection.execute("""
            UPDATE import_batches
            SET workflow = import_type
            WHERE workflow IS NULL OR TRIM(workflow) = ''
            """)
        connection.execute("""
            UPDATE import_batches
            SET dataset_kind = import_type
            WHERE dataset_kind IS NULL OR TRIM(dataset_kind) = ''
            """)
        connection.execute("""
            UPDATE import_batches
            SET total_raw_rows = record_count
            WHERE total_raw_rows = 0 AND record_count > 0
            """)
        connection.execute("""
            UPDATE import_batches
            SET valid_normalized_rows = record_count
            WHERE valid_normalized_rows = 0 AND record_count > 0
            """)
        connection.execute("""
            UPDATE import_batches
            SET started_at = created_at
            WHERE started_at IS NULL OR TRIM(started_at) = ''
            """)

        existing_corpus_hashes = {row["corpus_hash"] for row in connection.execute("""
                SELECT corpus_hash
                FROM corpus_versions
                WHERE corpus_hash IS NOT NULL AND TRIM(corpus_hash) != ''
                """).fetchall()}
        corpus_rows = connection.execute("""
            SELECT id, row_hash, corpus_hash
            FROM corpus_versions
            ORDER BY id ASC
            """).fetchall()
        for row in corpus_rows:
            corpus_hash = row["corpus_hash"]
            row_hash = row["row_hash"]
            if corpus_hash:
                continue
            if row_hash and row_hash not in existing_corpus_hashes:
                connection.execute(
                    """
                    UPDATE corpus_versions
                    SET corpus_hash = ?
                    WHERE id = ?
                    """,
                    (row_hash, row["id"]),
                )
                existing_corpus_hashes.add(row_hash)

        duplicate_hash_rows = connection.execute("""
            SELECT corpus_hash
            FROM corpus_versions
            WHERE corpus_hash IS NOT NULL AND TRIM(corpus_hash) != ''
            GROUP BY corpus_hash
            HAVING COUNT(*) > 1
            """).fetchall()
        for duplicate_row in duplicate_hash_rows:
            rows = connection.execute(
                """
                SELECT id
                FROM corpus_versions
                WHERE corpus_hash = ?
                ORDER BY id ASC
                """,
                (duplicate_row["corpus_hash"],),
            ).fetchall()
            for duplicate in rows[1:]:
                connection.execute(
                    """
                    UPDATE corpus_versions
                    SET corpus_hash = NULL
                    WHERE id = ?
                    """,
                    (duplicate["id"],),
                )

    def _ensure_patents_table(self, connection: sqlite3.Connection) -> None:
        if not self._table_exists(connection, "patents"):
            self._create_patents_table(connection)
        elif self._patents_schema_needs_migration(connection):
            self._migrate_patents_table(connection)

        self._add_missing_patent_columns(connection)
        self._backfill_patent_foundation_columns(connection)
        self._ensure_patent_indexes(connection)

    def _table_exists(self, connection: sqlite3.Connection, table_name: str) -> bool:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table_name,),
        ).fetchone()
        return row is not None

    def _create_patents_table(self, connection: sqlite3.Connection) -> None:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS patents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patent_id TEXT NOT NULL,
                analysis_id TEXT,
                publication_number TEXT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT NOT NULL,
                claims_text TEXT,
                claims_excerpt TEXT,
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
                candidate_application_areas TEXT NOT NULL DEFAULT '[]',
                patent_family TEXT,
                citation_count INTEGER,
                raw_source_ref TEXT,
                import_batch_id INTEGER,
                corpus_version_id INTEGER,
                row_hash TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patent_id, source),
                FOREIGN KEY(import_batch_id) REFERENCES import_batches(id),
                FOREIGN KEY(corpus_version_id) REFERENCES corpus_versions(id)
            )
            """)

    def _patents_schema_needs_migration(self, connection: sqlite3.Connection) -> bool:
        columns = connection.execute("PRAGMA table_info(patents)").fetchall()
        column_names = {row["name"] for row in columns}

        if "id" not in column_names:
            return True

        id_column = next(row for row in columns if row["name"] == "id")
        if id_column["pk"] != 1:
            return True

        return not self._has_patent_source_unique_constraint(connection)

    def _has_patent_source_unique_constraint(
        self, connection: sqlite3.Connection
    ) -> bool:
        indexes = connection.execute("PRAGMA index_list(patents)").fetchall()
        for index in indexes:
            if not index["unique"]:
                continue

            index_columns = connection.execute(
                f"PRAGMA index_info({index['name']})"
            ).fetchall()
            column_names = [row["name"] for row in index_columns]
            if column_names == ["patent_id", "source"]:
                return True

        return False

    def _migrate_patents_table(self, connection: sqlite3.Connection) -> None:
        connection.execute("ALTER TABLE patents RENAME TO patents_old")
        self._create_patents_table(connection)
        old_columns = self._table_column_names(connection, "patents_old")
        copy_columns = [
            column
            for column in self._PATENT_COPY_COLUMNS
            if self._can_copy_patent_column(column, old_columns)
        ]
        columns_sql = ",\n                ".join(copy_columns)
        select_sql = ",\n                ".join(
            self._patent_copy_expression(column, old_columns) for column in copy_columns
        )
        connection.execute(f"""
            INSERT INTO patents (
                {columns_sql}
            )
            SELECT
                {select_sql}
            FROM patents_old
            WHERE rowid IN (
                SELECT MAX(rowid)
                FROM patents_old
                GROUP BY patent_id, source
            )
            """)
        connection.execute("DROP TABLE patents_old")

    def _add_missing_patent_columns(self, connection: sqlite3.Connection) -> None:
        column_names = self._table_column_names(connection, "patents")
        for column_name, column_sql in self._PATENT_ADD_COLUMN_SQL.items():
            if column_name not in column_names:
                connection.execute(f"ALTER TABLE patents ADD COLUMN {column_sql}")

    def _backfill_patent_foundation_columns(
        self, connection: sqlite3.Connection
    ) -> None:
        column_names = self._table_column_names(connection, "patents")
        if {"analysis_id", "source", "patent_id"}.issubset(column_names):
            connection.execute("""
                UPDATE patents
                SET analysis_id = source || ':' || patent_id
                WHERE analysis_id IS NULL OR TRIM(analysis_id) = ''
                """)
        if {"publication_number", "patent_id"}.issubset(column_names):
            connection.execute("""
                UPDATE patents
                SET publication_number = patent_id
                WHERE publication_number IS NULL OR TRIM(publication_number) = ''
                """)
        if {"claims_excerpt", "claims_text"}.issubset(column_names):
            connection.execute("""
                UPDATE patents
                SET claims_excerpt = claims_text
                WHERE (claims_excerpt IS NULL OR TRIM(claims_excerpt) = '')
                    AND claims_text IS NOT NULL
                    AND TRIM(claims_text) != ''
                """)
        if "candidate_application_areas" in column_names:
            connection.execute("""
                UPDATE patents
                SET candidate_application_areas = '[]'
                WHERE candidate_application_areas IS NULL
                    OR TRIM(candidate_application_areas) = ''
                """)
        if {"updated_at", "created_at"}.issubset(column_names):
            connection.execute("""
                UPDATE patents
                SET updated_at = created_at
                WHERE updated_at IS NULL OR TRIM(updated_at) = ''
                """)

    def _ensure_patent_indexes(self, connection: sqlite3.Connection) -> None:
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_patents_analysis_id
            ON patents(analysis_id)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_patents_publication_number
            ON patents(publication_number)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_patents_import_batch
            ON patents(import_batch_id)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_patents_corpus_version
            ON patents(corpus_version_id)
            """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_patents_row_hash
            ON patents(row_hash)
            """)

    def _table_column_names(
        self, connection: sqlite3.Connection, table_name: str
    ) -> set[str]:
        columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in columns}

    def _create_import_batch(
        self,
        connection: sqlite3.Connection,
        *,
        workflow: str,
        dataset_kind: str,
        source_label: str,
        source_path: str | None = None,
        source_file_hash: str | None = None,
        corpus_hash: str | None = None,
        status: str = "created",
        total_raw_rows: int = 0,
        valid_normalized_rows: int = 0,
        skipped_rows: int = 0,
        summary: dict[str, Any] | None = None,
    ) -> int:
        cursor = connection.execute(
            """
            INSERT INTO import_batches (
                workflow,
                dataset_kind,
                import_type,
                source_label,
                source_path,
                source_file_hash,
                corpus_hash,
                total_raw_rows,
                valid_normalized_rows,
                skipped_rows,
                record_count,
                status,
                started_at,
                created_at,
                summary_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP, ?)
            """,
            (
                workflow,
                dataset_kind,
                workflow,
                source_label,
                source_path,
                source_file_hash,
                corpus_hash,
                total_raw_rows,
                valid_normalized_rows,
                skipped_rows,
                valid_normalized_rows,
                status,
                self._dumps_json(summary or {}),
            ),
        )
        return int(cursor.lastrowid)

    def _update_import_batch(
        self,
        connection: sqlite3.Connection,
        import_batch_id: int,
        *,
        status: str,
        corpus_version_id: int | None = None,
        total_raw_rows: int | None = None,
        valid_normalized_rows: int | None = None,
        skipped_rows: int | None = None,
        upserted_rows: int | None = None,
        inserted_rows: int | None = None,
        updated_rows: int | None = None,
        unchanged_rows: int | None = None,
        summary: dict[str, Any] | None = None,
        error_message: str | None = None,
        completed: bool = False,
    ) -> None:
        assignments: list[str] = ["status = ?"]
        values: list[Any] = [status]
        optional_values = {
            "corpus_version_id": corpus_version_id,
            "total_raw_rows": total_raw_rows,
            "valid_normalized_rows": valid_normalized_rows,
            "skipped_rows": skipped_rows,
            "upserted_rows": upserted_rows,
            "inserted_rows": inserted_rows,
            "updated_rows": updated_rows,
            "unchanged_rows": unchanged_rows,
            "summary_json": self._dumps_json(summary) if summary is not None else None,
            "error_message": error_message,
        }
        for column_name, value in optional_values.items():
            if value is None:
                continue
            assignments.append(f"{column_name} = ?")
            values.append(value)
            if column_name == "valid_normalized_rows":
                assignments.append("record_count = ?")
                values.append(value)

        if completed:
            assignments.append("completed_at = CURRENT_TIMESTAMP")

        values.append(import_batch_id)
        assignments_sql = ",\n                ".join(assignments)
        connection.execute(
            f"""
            UPDATE import_batches
            SET {assignments_sql}
            WHERE id = ?
            """,
            values,
        )

    def _get_import_batch(
        self, connection: sqlite3.Connection, import_batch_id: int
    ) -> dict[str, Any]:
        row = connection.execute(
            """
            SELECT *
            FROM import_batches
            WHERE id = ?
            """,
            (import_batch_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Import batch not found: {import_batch_id}.")
        return self._row_to_dict(row)

    def _get_corpus_version_by_hash(
        self, connection: sqlite3.Connection, corpus_hash: str
    ) -> dict[str, Any] | None:
        row = connection.execute(
            """
            SELECT *
            FROM corpus_versions
            WHERE corpus_hash = ?
            """,
            (corpus_hash,),
        ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def _create_corpus_version(
        self,
        connection: sqlite3.Connection,
        *,
        corpus_hash: str,
        dataset_kind: str,
        source_label: str,
        label: str | None = None,
        source_path: str | None = None,
        source_file_hash: str | None = None,
        source_counts: dict[str, int] | None = None,
        summary: dict[str, Any] | None = None,
        row_count: int = 0,
        created_from_import_batch_id: int | None = None,
    ) -> dict[str, Any]:
        existing = self._get_corpus_version_by_hash(connection, corpus_hash)
        if existing is not None:
            return existing

        base_label = label or f"{dataset_kind}-{corpus_hash[:12]}"
        candidate_label = base_label
        attempt = 1
        while True:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO corpus_versions (
                        version_label,
                        corpus_hash,
                        dataset_kind,
                        source_label,
                        source_path,
                        source_file_hash,
                        source_counts_json,
                        summary_json,
                        created_from_import_batch_id,
                        hash_algorithm,
                        row_hash_version,
                        row_count,
                        row_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candidate_label,
                        corpus_hash,
                        dataset_kind,
                        source_label,
                        source_path,
                        source_file_hash,
                        self._dumps_json(source_counts or {}),
                        self._dumps_json(summary or {}),
                        created_from_import_batch_id,
                        self.HASH_ALGORITHM,
                        self.ROW_HASH_VERSION,
                        row_count,
                        corpus_hash,
                    ),
                )
            except sqlite3.IntegrityError:
                existing = self._get_corpus_version_by_hash(connection, corpus_hash)
                if existing is not None:
                    return existing
                attempt += 1
                candidate_label = f"{base_label}-{attempt}"
                continue

            corpus_version = self._get_corpus_version(connection, int(cursor.lastrowid))
            return corpus_version

    def _get_or_create_corpus_version(
        self,
        connection: sqlite3.Connection,
        *,
        corpus_hash: str,
        dataset_kind: str,
        source_label: str,
        label: str | None = None,
        source_path: str | None = None,
        source_file_hash: str | None = None,
        source_counts: dict[str, int] | None = None,
        summary: dict[str, Any] | None = None,
        row_count: int = 0,
        created_from_import_batch_id: int | None = None,
    ) -> dict[str, Any]:
        existing = self._get_corpus_version_by_hash(connection, corpus_hash)
        if existing is not None:
            return existing
        return self._create_corpus_version(
            connection,
            corpus_hash=corpus_hash,
            dataset_kind=dataset_kind,
            source_label=source_label,
            label=label,
            source_path=source_path,
            source_file_hash=source_file_hash,
            source_counts=source_counts,
            summary=summary,
            row_count=row_count,
            created_from_import_batch_id=created_from_import_batch_id,
        )

    def _get_corpus_version(
        self, connection: sqlite3.Connection, corpus_version_id: int
    ) -> dict[str, Any]:
        row = connection.execute(
            """
            SELECT *
            FROM corpus_versions
            WHERE id = ?
            """,
            (corpus_version_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Corpus version not found: {corpus_version_id}.")
        return self._row_to_dict(row)

    def _activate_corpus_version(
        self, connection: sqlite3.Connection, corpus_version_id: int
    ) -> dict[str, Any]:
        self._get_corpus_version(connection, corpus_version_id)
        connection.execute("UPDATE corpus_versions SET is_active = 0")
        connection.execute(
            """
            UPDATE corpus_versions
            SET is_active = 1,
                activated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (corpus_version_id,),
        )
        return self._get_corpus_version(connection, corpus_version_id)

    def _get_active_corpus_version(
        self, connection: sqlite3.Connection
    ) -> dict[str, Any] | None:
        row = connection.execute("""
            SELECT *
            FROM corpus_versions
            WHERE is_active = 1
            ORDER BY activated_at DESC, id DESC
            LIMIT 1
            """).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def _fetch_patent_hash_index(
        self, connection: sqlite3.Connection
    ) -> dict[str, str | None]:
        rows = connection.execute("""
            SELECT analysis_id, row_hash
            FROM patents
            ORDER BY analysis_id ASC
            """).fetchall()
        return {row["analysis_id"]: row["row_hash"] for row in rows}

    def _upsert_patents_with_import_metadata(
        self,
        connection: sqlite3.Connection,
        records: list[PatentRecord],
        row_hashes: dict[str, str],
        import_batch_id: int,
        corpus_version_id: int | None,
    ) -> dict[str, int]:
        existing_hashes = self._fetch_patent_hash_index(connection)
        inserted_rows = 0
        updated_rows = 0
        unchanged_rows = 0
        columns = (
            *self._PATENT_UPSERT_COLUMNS,
            "import_batch_id",
            "corpus_version_id",
            "row_hash",
        )
        columns_sql = ",\n                        ".join(columns)
        placeholders_sql = ", ".join("?" for _ in columns)
        update_columns = [
            column for column in columns if column not in {"patent_id", "source"}
        ]
        updates_sql = ",\n                        ".join(
            f"{column} = excluded.{column}" for column in update_columns
        )

        for record in records:
            row_hash = row_hashes[record.analysis_id]
            previous_hash = existing_hashes.get(record.analysis_id)
            if record.analysis_id not in existing_hashes:
                inserted_rows += 1
            elif previous_hash == row_hash:
                unchanged_rows += 1
            else:
                updated_rows += 1

            connection.execute(
                f"""
                INSERT INTO patents (
                    {columns_sql}
                )
                VALUES ({placeholders_sql})
                ON CONFLICT(patent_id, source) DO UPDATE SET
                    {updates_sql},
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    *self._record_to_row(record),
                    import_batch_id,
                    corpus_version_id,
                    row_hash,
                ),
            )

        upserted_rows = len(records)
        return {
            "upserted_rows": upserted_rows,
            "inserted_rows": inserted_rows,
            "updated_rows": updated_rows,
            "unchanged_rows": unchanged_rows,
        }

    def _prune_patents_not_in_corpus(
        self, connection: sqlite3.Connection, analysis_ids: set[str]
    ) -> int:
        if not analysis_ids:
            cursor = connection.execute("DELETE FROM patents")
            return int(cursor.rowcount)

        placeholders = ", ".join("?" for _ in analysis_ids)
        cursor = connection.execute(
            f"""
            DELETE FROM patents
            WHERE analysis_id NOT IN ({placeholders})
            """,
            tuple(sorted(analysis_ids)),
        )
        return int(cursor.rowcount)

    def _backfill_patent_versioning_state(self, connection: sqlite3.Connection) -> None:
        if not self._table_exists(connection, "patents"):
            return

        patent_rows = self._fetch_patent_rows_with_metadata(connection)
        if not patent_rows:
            return

        row_hashes: dict[str, str] = {}
        for row in patent_rows:
            record = self._row_to_record(row)
            row_hash = row["row_hash"] or self.row_hash_for_record(record)
            row_hashes[record.analysis_id] = row_hash
            if not row["row_hash"]:
                connection.execute(
                    """
                    UPDATE patents
                    SET row_hash = ?
                    WHERE id = ?
                    """,
                    (row_hash, row["id"]),
                )

        if self._get_active_corpus_version(connection) is not None:
            return

        corpus_hash = self.corpus_hash_for_row_hashes(row_hashes)
        source_counts: dict[str, int] = {}
        for row in patent_rows:
            source = row["source"]
            source_counts[source] = source_counts.get(source, 0) + 1

        import_batch_id = self._create_import_batch(
            connection,
            workflow="migration_backfill",
            dataset_kind="legacy_sqlite",
            source_label="legacy-sqlite",
            corpus_hash=corpus_hash,
            total_raw_rows=len(patent_rows),
            valid_normalized_rows=len(patent_rows),
            skipped_rows=0,
            summary={
                "source": "legacy-sqlite",
                "dataset_kind": "legacy_sqlite",
                "corpus_hash": corpus_hash,
                "source_counts": source_counts,
            },
        )
        corpus_version = self._get_or_create_corpus_version(
            connection,
            corpus_hash=corpus_hash,
            dataset_kind="legacy_sqlite",
            source_label="legacy-sqlite",
            label=f"legacy-sqlite-{corpus_hash[:12]}",
            source_counts=source_counts,
            summary={
                "source": "legacy-sqlite",
                "dataset_kind": "legacy_sqlite",
                "corpus_hash": corpus_hash,
                "source_counts": source_counts,
            },
            row_count=len(patent_rows),
            created_from_import_batch_id=import_batch_id,
        )
        corpus_version_id = int(corpus_version["id"])
        connection.execute(
            """
            UPDATE patents
            SET import_batch_id = ?,
                corpus_version_id = ?
            """,
            (import_batch_id, corpus_version_id),
        )
        self._activate_corpus_version(connection, corpus_version_id)
        self._update_import_batch(
            connection,
            import_batch_id,
            status="completed",
            corpus_version_id=corpus_version_id,
            total_raw_rows=len(patent_rows),
            valid_normalized_rows=len(patent_rows),
            skipped_rows=0,
            upserted_rows=len(patent_rows),
            inserted_rows=0,
            updated_rows=len(patent_rows),
            unchanged_rows=0,
            completed=True,
        )

    def _fetch_patent_rows_with_metadata(
        self, connection: sqlite3.Connection
    ) -> list[sqlite3.Row]:
        columns = (
            "id",
            *self._PATENT_FETCH_COLUMNS,
            "import_batch_id",
            "corpus_version_id",
            "row_hash",
        )
        columns_sql = ",\n                ".join(columns)
        return connection.execute(f"""
            SELECT
                {columns_sql}
            FROM patents
            ORDER BY analysis_id ASC
            """).fetchall()

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def _can_copy_patent_column(self, column: str, old_columns: set[str]) -> bool:
        if column in old_columns:
            return True
        if column == "analysis_id":
            return {"source", "patent_id"}.issubset(old_columns)
        if column == "publication_number":
            return "patent_id" in old_columns
        if column == "updated_at":
            return True
        if column == "claims_excerpt":
            return "claims_text" in old_columns
        return True

    def _patent_copy_expression(self, column: str, old_columns: set[str]) -> str:
        if column in old_columns:
            return column
        if column == "analysis_id":
            return "source || ':' || patent_id"
        if column == "publication_number":
            return "patent_id"
        if column == "claims_excerpt":
            return "claims_text"
        if column in {
            "inventors",
            "ipc_codes",
            "cpc_codes",
            "keywords",
            "candidate_application_areas",
        }:
            return "'[]'"
        if column == "updated_at" and "created_at" in old_columns:
            return "created_at"
        if column in {"created_at", "updated_at"}:
            return "CURRENT_TIMESTAMP"
        if column in {"title", "abstract"}:
            return "''"
        return "NULL"

    def _record_to_row(self, record: PatentRecord) -> tuple[Any, ...]:
        return (
            record.patent_id,
            record.analysis_id,
            record.publication_number or record.patent_id,
            record.source.value,
            record.title,
            record.abstract,
            record.claims_text,
            record.claims_excerpt,
            record.description_text,
            record.assignee,
            self._dumps_list(record.inventors),
            record.publication_date,
            record.filing_date,
            self._dumps_list(record.ipc_codes),
            self._dumps_list(record.cpc_codes),
            record.country,
            record.language,
            record.source_url,
            self._dumps_list(record.keywords),
            self._dumps_list(record.candidate_application_areas),
            record.patent_family,
            record.citation_count,
            record.raw_source_ref,
        )

    def _row_to_record(self, row: sqlite3.Row) -> PatentRecord:
        return PatentRecord(
            patent_id=row["patent_id"],
            source=SourceType(row["source"]),
            title=row["title"],
            abstract=row["abstract"],
            publication_number=row["publication_number"] or row["patent_id"],
            claims_text=row["claims_text"],
            claims_excerpt=row["claims_excerpt"],
            description_text=row["description_text"],
            assignee=row["assignee"],
            inventors=self._loads_list(row["inventors"]),
            publication_date=row["publication_date"],
            filing_date=row["filing_date"],
            ipc_codes=self._loads_list(row["ipc_codes"]),
            cpc_codes=self._loads_list(row["cpc_codes"]),
            country=row["country"],
            language=row["language"],
            source_url=row["source_url"],
            keywords=self._loads_list(row["keywords"]),
            candidate_application_areas=self._loads_list(
                row["candidate_application_areas"]
            ),
            patent_family=row["patent_family"],
            citation_count=self._loads_int(row["citation_count"]),
            raw_source_ref=row["raw_source_ref"],
        )

    @classmethod
    def _row_hash_payload(cls, record: PatentRecord) -> dict[str, Any]:
        values = {
            "source": record.source.value,
            "patent_id": record.patent_id,
            "publication_number": record.publication_number or record.patent_id,
            "title": record.title,
            "abstract": record.abstract,
            "claims_text": record.claims_text,
            "claims_excerpt": record.claims_excerpt,
            "description_text": record.description_text,
            "assignee": record.assignee,
            "inventors": list(record.inventors),
            "publication_date": record.publication_date,
            "filing_date": record.filing_date,
            "ipc_codes": list(record.ipc_codes),
            "cpc_codes": list(record.cpc_codes),
            "country": record.country,
            "language": record.language,
            "source_url": record.source_url,
            "keywords": list(record.keywords),
            "candidate_application_areas": list(record.candidate_application_areas),
            "patent_family": record.patent_family,
            "citation_count": record.citation_count,
            "raw_source_ref": record.raw_source_ref,
        }
        return {field: values[field] for field in cls._ROW_HASH_FIELDS}

    @classmethod
    def _sha256_json(cls, payload: dict[str, Any]) -> str:
        json_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()

    def _dumps_json(self, value: dict[str, Any]) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def _dumps_list(self, values: list[str]) -> str:
        return json.dumps(values, ensure_ascii=False)

    def _loads_list(self, value: str | None) -> list[str]:
        if not value:
            return []

        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return []

        if not isinstance(loaded, list):
            return []

        return [str(item).strip() for item in loaded if str(item).strip()]

    def _loads_int(self, value: Any) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None
