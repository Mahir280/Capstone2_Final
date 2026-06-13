"""Normalize imported patent rows into the canonical patent model."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from src.models.enums import SourceType
from src.models.patent import PatentRecord


class PatentNormalizer:
    """Convert practical imported row shapes into PatentRecord instances."""

    field_aliases: dict[str, tuple[str, ...]] = {
        "patent_id": ("patent_id", "publication_number", "id", "patent_number"),
        "publication_number": ("publication_number",),
        "title": ("title", "invention_title"),
        "abstract": ("abstract", "summary"),
        "claims_text": ("claims_text", "claims", "claims_excerpt"),
        "claims_excerpt": ("claims_excerpt",),
        "description_text": ("description_text", "description"),
        "assignee": ("assignee", "applicant", "assignees", "applicants"),
        "inventors": ("inventors", "inventor"),
        "publication_date": ("publication_date", "pub_date"),
        "filing_date": ("filing_date",),
        "ipc_codes": ("ipc_codes", "ipc"),
        "cpc_codes": ("cpc_codes", "cpc"),
        "country": ("country",),
        "language": ("language",),
        "source_url": ("source_url", "url"),
        "keywords": ("keywords",),
        "candidate_application_areas": (
            "candidate_application_areas",
            "application_areas",
            "candidate_applications",
        ),
        "patent_family": ("patent_family", "family", "family_id"),
        "citation_count": ("citation_count", "citations"),
        "raw_source_ref": ("raw_source_ref", "source_ref"),
    }

    def normalize(
        self, raw_record: Mapping[str, Any], source: SourceType | str
    ) -> PatentRecord:
        """Normalize one raw record, raising ValueError for invalid rows."""
        lookup = self._build_lookup(raw_record)

        patent_id = self._required_text(lookup, "patent_id")
        title = self._required_text(lookup, "title")

        return PatentRecord(
            patent_id=patent_id,
            source=self._coerce_source(source),
            title=title,
            abstract=self._text_field(lookup, "abstract") or "",
            publication_number=self._text_field(lookup, "publication_number")
            or patent_id,
            claims_text=self._text_field(lookup, "claims_text"),
            claims_excerpt=self._text_field(lookup, "claims_excerpt"),
            description_text=self._text_field(lookup, "description_text"),
            assignee=self._text_field(lookup, "assignee"),
            inventors=self._list_field(lookup, "inventors", split_commas=False),
            publication_date=self._text_field(lookup, "publication_date"),
            filing_date=self._text_field(lookup, "filing_date"),
            ipc_codes=self._list_field(lookup, "ipc_codes", split_commas=True),
            cpc_codes=self._list_field(lookup, "cpc_codes", split_commas=True),
            country=self._text_field(lookup, "country"),
            language=self._text_field(lookup, "language"),
            source_url=self._text_field(lookup, "source_url"),
            keywords=self._list_field(lookup, "keywords", split_commas=True),
            candidate_application_areas=self._list_field(
                lookup,
                "candidate_application_areas",
                split_commas=False,
            ),
            patent_family=self._text_field(lookup, "patent_family"),
            citation_count=self._integer_field(lookup, "citation_count"),
            raw_source_ref=self._text_field(lookup, "raw_source_ref"),
        )

    def _build_lookup(self, raw_record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            self._canonical_key(str(key)): value
            for key, value in raw_record.items()
            if key is not None
        }

    def _required_text(self, lookup: dict[str, Any], field_name: str) -> str:
        value = self._text_field(lookup, field_name)
        if value is None:
            raise ValueError(f"Missing required field: {field_name}.")
        return value

    def _text_field(self, lookup: dict[str, Any], field_name: str) -> str | None:
        return self._clean_text(self._first_value(lookup, field_name))

    def _list_field(
        self, lookup: dict[str, Any], field_name: str, *, split_commas: bool
    ) -> list[str]:
        return self._clean_list(
            self._first_value(lookup, field_name), split_commas=split_commas
        )

    def _integer_field(self, lookup: dict[str, Any], field_name: str) -> int | None:
        return self._clean_integer(self._first_value(lookup, field_name))

    def _first_value(self, lookup: dict[str, Any], field_name: str) -> Any:
        for alias in self.field_aliases[field_name]:
            value = lookup.get(self._canonical_key(alias))
            if not self._is_missing_value(value):
                return value
        return None

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, (list, tuple, set)):
            pieces = [self._clean_text(item) for item in value]
            text = " ".join(piece for piece in pieces if piece)
        else:
            text = str(value).strip()

        if not text or text.lower() in {"none", "null", "nan"}:
            return None

        return text

    def _clean_list(self, value: Any, *, split_commas: bool) -> list[str]:
        if value is None:
            return []

        if isinstance(value, str):
            text = value.strip()
            if not text or text.lower() in {"none", "null", "nan"}:
                return []

            parsed = self._parse_json_list(text)
            if parsed is not None:
                return self._clean_list(parsed, split_commas=split_commas)

            separator_pattern = r"[;|,]+" if split_commas else r"[;|]+"
            return self._clean_list_parts(
                re.split(separator_pattern, text), split_commas=split_commas
            )

        if isinstance(value, (list, tuple, set)):
            return self._clean_list_parts(value, split_commas=split_commas)

        text_value = self._clean_text(value)
        return [text_value] if text_value else []

    def _clean_list_parts(self, values: Any, *, split_commas: bool) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            if isinstance(value, (list, tuple, set)):
                cleaned.extend(self._clean_list(value, split_commas=split_commas))
                continue

            text = self._clean_text(value)
            if text:
                cleaned.append(text)

        return cleaned

    def _clean_integer(self, value: Any) -> int | None:
        if value is None:
            return None

        if isinstance(value, (list, tuple, set)):
            for item in value:
                cleaned = self._clean_integer(item)
                if cleaned is not None:
                    return cleaned
            return None

        text = self._clean_text(value)
        if text is None:
            return None

        normalized = text.replace(",", "")
        try:
            return int(normalized)
        except ValueError:
            try:
                number = float(normalized)
            except ValueError:
                return None

        return int(number) if number.is_integer() else None

    def _parse_json_list(self, text: str) -> list[Any] | None:
        if not (text.startswith("[") and text.endswith("]")):
            return None

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None

        return parsed if isinstance(parsed, list) else None

    def _canonical_key(self, key: str) -> str:
        return key.strip().lower().replace("-", "_").replace(" ", "_")

    def _is_missing_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return self._clean_text(value) is None
        if isinstance(value, (list, tuple, set)):
            return len(value) == 0
        return False

    def _coerce_source(self, source: SourceType | str) -> SourceType:
        if isinstance(source, SourceType):
            return source

        try:
            return SourceType(str(source))
        except ValueError as exc:
            raise ValueError(f"Unsupported source type: {source}.") from exc
