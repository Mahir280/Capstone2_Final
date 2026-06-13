"""Quality checks for curated patent corpus intake rows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from src.models.enums import SourceType

CANONICAL_CORPUS_SCHEMA_COLUMNS = (
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
CANONICAL_CORPUS_ACCEPTED_REQUIRED_FIELDS = (
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
)
CANONICAL_CORPUS_CLASSIFICATION_FIELDS = ("ipc_codes", "cpc_codes")
CANONICAL_CORPUS_STRONGLY_PREFERRED_FIELDS = (
    "claims_excerpt",
    "patent_family",
    "citation_count",
)
REVIEW_NEEDED_SCHEMA_COLUMNS = (
    *CANONICAL_CORPUS_SCHEMA_COLUMNS,
    "review_reason",
    "missing_fields",
    "source_notes",
)
BAD_CORPUS_LITERAL_VALUES = {
    "unknown",
    "unknown authority",
    "n/a",
    "na",
    "tbd",
    "placeholder",
    "none",
    "null",
    "nan",
    "not available",
    "not applicable",
}
EXPECTED_CORPUS_SOURCE_LABELS = {
    "EPO",
    "EUROPEAN_PATENT_OFFICE",
    "USPTO",
    "US_PATENT_AND_TRADEMARK_OFFICE",
    "UNITED_STATES_PATENT_AND_TRADEMARK_OFFICE",
    "TPO",
    "TURKPATENT",
    "TURKPATENT_TPO",
    "TPO_TURKPATENT",
    "TURK_PATENT",
    "TURKISH_PATENT_OFFICE",
    *(source_type.value for source_type in SourceType),
}


@dataclass(slots=True)
class CorpusQualityAudit:
    """Review details for one candidate corpus row."""

    missing_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)
    review_reasons: list[str] = field(default_factory=list)
    strongly_preferred_missing_fields: list[str] = field(default_factory=list)

    @property
    def is_accepted(self) -> bool:
        """Return whether the row meets the strict accepted-record gate."""
        return (
            not self.missing_fields
            and not self.invalid_fields
            and not self.review_reasons
        )


def audit_corpus_row(row: Mapping[str, Any]) -> CorpusQualityAudit:
    """Check a future candidate corpus row against strict intake rules."""
    audit = CorpusQualityAudit()

    for field_name in CANONICAL_CORPUS_ACCEPTED_REQUIRED_FIELDS:
        value = _value_for_field(row, field_name)
        if _is_empty(value):
            audit.missing_fields.append(field_name)
        elif _is_bad_literal(value):
            audit.invalid_fields.append(field_name)

    for field_name in CANONICAL_CORPUS_STRONGLY_PREFERRED_FIELDS:
        if _is_empty(_value_for_field(row, field_name)):
            audit.strongly_preferred_missing_fields.append(field_name)

    missing_all_classification_fields = all(
        _is_empty_or_bad_literal(_value_for_field(row, field))
        for field in CANONICAL_CORPUS_CLASSIFICATION_FIELDS
    )
    if missing_all_classification_fields:
        audit.review_reasons.append("missing both ipc_codes and cpc_codes")

    source_value = _value_for_field(row, "source")
    if not _is_empty(source_value) and not _is_expected_source(source_value):
        audit.invalid_fields.append("source")
        audit.review_reasons.append(
            "source must be USPTO, EPO, TURKPATENT/TPO, "
            "or an existing project source enum"
        )

    source_url = _value_for_field(row, "source_url")
    if (
        _is_empty(source_url)
        or _is_bad_literal(source_url)
        or not _is_valid_url(source_url)
    ):
        if "source_url" not in audit.invalid_fields:
            audit.invalid_fields.append("source_url")
        audit.review_reasons.append("source_url must be a non-empty absolute URL")

    for field_name in CANONICAL_CORPUS_SCHEMA_COLUMNS:
        if (
            _is_bad_literal(_value_for_field(row, field_name))
            and field_name not in audit.invalid_fields
        ):
            audit.invalid_fields.append(field_name)

    return audit


def _value_for_field(row: Mapping[str, Any], field_name: str) -> Any:
    canonical_field_name = _canonical_name(field_name)
    for key, value in row.items():
        if _canonical_name(str(key)) == canonical_field_name:
            return value
    return None


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    return False


def _is_empty_or_bad_literal(value: Any) -> bool:
    return _is_empty(value) or _is_bad_literal(value)


def _is_bad_literal(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, set)):
        return any(_is_bad_literal(item) for item in value)
    return str(value).strip().lower() in BAD_CORPUS_LITERAL_VALUES


def _is_valid_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_expected_source(value: Any) -> bool:
    return _canonical_source_label(str(value)) in EXPECTED_CORPUS_SOURCE_LABELS


def _canonical_name(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _canonical_source_label(value: str) -> str:
    return value.strip().upper().replace("-", "_").replace(" ", "_").replace("/", "_")
