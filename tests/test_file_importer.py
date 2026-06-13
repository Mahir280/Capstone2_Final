"""Tests for local and uploaded patent file imports."""

from __future__ import annotations

from io import BytesIO

import pytest

from src.acquisition.file_importer import FileImporter


class NamedBytesIO(BytesIO):
    """Tiny uploaded-file stand-in with a name attribute."""

    def __init__(self, content: bytes, name: str) -> None:
        super().__init__(content)
        self.name = name


def test_file_importer_reads_csv_records(tmp_path) -> None:
    csv_path = tmp_path / "patents.csv"
    csv_path.write_text(
        "patent_id,title,abstract\n" "US-1,Fiber sensor,Wearable sensor abstract\n",
        encoding="utf-8",
    )

    records = FileImporter().import_file(csv_path)

    assert records == [
        {
            "patent_id": "US-1",
            "title": "Fiber sensor",
            "abstract": "Wearable sensor abstract",
        }
    ]


def test_file_importer_reads_json_records_from_uploaded_file() -> None:
    uploaded_file = NamedBytesIO(
        b'[{"id": "US-2", "title": "Textile electrode"}]', "patents.json"
    )

    records = FileImporter().import_file(uploaded_file)

    assert records == [{"id": "US-2", "title": "Textile electrode"}]


def test_file_importer_handles_empty_files(tmp_path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    assert FileImporter().import_file(csv_path) == []


def test_file_importer_rejects_unsupported_types(tmp_path) -> None:
    text_path = tmp_path / "patents.txt"
    text_path.write_text("not a supported import", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported import file type"):
        FileImporter().import_file(text_path)
