"""Simple CSV and JSON patent file imports."""

from __future__ import annotations

import csv
import json
from io import StringIO
from os import PathLike
from pathlib import Path
from typing import Any, BinaryIO, TextIO

FileInput = str | PathLike[str] | BinaryIO | TextIO


class FileImporter:
    """Read local or uploaded CSV/JSON files into raw dictionaries."""

    supported_extensions: tuple[str, ...] = (".csv", ".json")

    def __init__(self, encoding: str = "utf-8-sig") -> None:
        self.encoding = encoding

    def import_file(
        self, file_source: FileInput, import_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Read supported file content and return raw record dictionaries."""
        extension = self.resolve_extension(file_source, import_type)
        text = self._read_text(file_source)

        if not text.strip():
            return []

        if extension == ".csv":
            return self._import_csv(text)
        if extension == ".json":
            return self._import_json(text)

        raise ValueError(self._unsupported_message(extension))

    def read_csv_headers(
        self, file_source: FileInput, import_type: str | None = None
    ) -> list[str]:
        """Read CSV headers without importing rows."""
        extension = self.resolve_extension(file_source, import_type)
        if extension != ".csv":
            raise ValueError("CSV column validation requires a CSV import file.")

        text = self._read_text(file_source)
        if not text.strip():
            return []

        reader = csv.DictReader(StringIO(text))
        if reader.fieldnames is None:
            return []

        return [
            str(field_name).strip()
            for field_name in reader.fieldnames
            if field_name is not None and str(field_name).strip()
        ]

    def resolve_extension(
        self, file_source: FileInput, import_type: str | None = None
    ) -> str:
        """Resolve the intended import extension from an explicit type or name."""
        candidates = [import_type, self._name_from_source(file_source)]
        for candidate in candidates:
            extension = self._extension_from_candidate(candidate)
            if extension:
                return extension

        raise ValueError(self._unsupported_message(None))

    def _import_csv(self, text: str) -> list[dict[str, Any]]:
        reader = csv.DictReader(StringIO(text))
        if reader.fieldnames is None:
            return []

        records: list[dict[str, Any]] = []
        for row in reader:
            cleaned_row = {
                str(key).strip(): value
                for key, value in row.items()
                if key is not None and str(key).strip()
            }
            if self._row_has_content(cleaned_row):
                records.append(cleaned_row)

        return records

    def _import_json(self, text: str) -> list[dict[str, Any]]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON import file: {exc.msg}") from exc

        records = self._records_from_json_payload(payload)
        return [record for record in records if self._row_has_content(record)]

    def _records_from_json_payload(self, payload: Any) -> list[dict[str, Any]]:
        if payload == {}:
            return []

        if isinstance(payload, list):
            return self._validate_json_record_list(payload)

        if isinstance(payload, dict):
            for key in ("records", "patents", "data", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return self._validate_json_record_list(value)

            return [dict(payload)]

        raise ValueError("JSON import must contain an object or a list of objects.")

    def _validate_json_record_list(self, records: list[Any]) -> list[dict[str, Any]]:
        validated: list[dict[str, Any]] = []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                raise ValueError(
                    f"JSON import row {index} must be an object, "
                    f"not {type(record).__name__}."
                )
            validated.append(dict(record))

        return validated

    def _read_text(self, file_source: FileInput) -> str:
        if isinstance(file_source, (str, PathLike)):
            return Path(file_source).read_text(encoding=self.encoding)

        if hasattr(file_source, "getvalue"):
            content = file_source.getvalue()
        else:
            if hasattr(file_source, "seek"):
                file_source.seek(0)
            content = file_source.read()

        if isinstance(content, bytes):
            return content.decode(self.encoding)
        if isinstance(content, str):
            return content

        raise ValueError("Imported file content must be text or bytes.")

    def _extension_from_candidate(self, candidate: str | None) -> str | None:
        if not candidate:
            return None

        value = candidate.strip()
        if not value:
            return None

        suffix = Path(value).suffix.lower()
        if suffix in self.supported_extensions:
            return suffix

        normalized = value.lower().strip().lstrip(".").replace("-", "_")
        if normalized in {"csv", "csv_import", "text/csv"}:
            return ".csv"
        if normalized in {"json", "json_import", "application/json"}:
            return ".json"

        if suffix:
            raise ValueError(self._unsupported_message(suffix))

        return None

    def _name_from_source(self, file_source: FileInput) -> str | None:
        if isinstance(file_source, (str, PathLike)):
            return str(file_source)

        name = getattr(file_source, "name", None)
        return str(name) if name else None

    def _row_has_content(self, row: dict[str, Any]) -> bool:
        for value in row.values():
            if value is not None and str(value).strip():
                return True
        return False

    def _unsupported_message(self, extension: str | None) -> str:
        expected = ", ".join(self.supported_extensions)
        if extension:
            return f"Unsupported import file type '{extension}'. Expected: {expected}."
        return f"Unsupported import file type. Expected: {expected}."
