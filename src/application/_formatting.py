"""Presentation-safe labels shared by application services and API responses."""

import re
from collections import Counter
from typing import Any

from src.models.enums import SourceType
from src.models.patent import PatentRecord

UNKNOWN_LABEL = "Unknown"
UNKNOWN_AUTHORITY_LABEL = "Unknown authority"
_YEAR_PATTERN = re.compile(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)")
_SOURCE_AUTHORITY_LABELS = {
    SourceType.EPO.value: "EPO",
    SourceType.USPTO.value: "USPTO",
    SourceType.TURKPATENT.value: "TURKPATENT/TPO",
}
_IMPORT_METHOD_LABELS = {
    SourceType.CSV_IMPORT.value: "CSV file import",
    SourceType.JSON_IMPORT.value: "JSON file import",
}
_SOURCE_LABELED_RECORD = "Source-labeled patent record"


def format_patent_authority(record: object) -> str:
    """Return the public patent authority label for a record-like object."""
    source_value = source_value_for(record)
    authority_label = _SOURCE_AUTHORITY_LABELS.get(source_value)
    if authority_label is not None:
        return authority_label

    if source_value in _IMPORT_METHOD_LABELS:
        patent_id = patent_id_value(record).upper()
        if patent_id.startswith("US"):
            return "USPTO"
        if patent_id.startswith("EP"):
            return "EPO"
        if patent_id.startswith("TR"):
            return "TURKPATENT/TPO"

    return UNKNOWN_AUTHORITY_LABEL


def format_import_method(record: object) -> str:
    """Return the local import method without implying live source fetching."""
    source_value = source_value_for(record)
    import_label = _IMPORT_METHOD_LABELS.get(source_value)
    if import_label is not None:
        return import_label
    if source_value in _SOURCE_AUTHORITY_LABELS:
        return _SOURCE_LABELED_RECORD
    return "Prepared/imported source record"


def source_value_for(record: object) -> str:
    """Return a normalized source value for record-like objects and DTO nodes."""
    source = getattr(record, "source", "")
    if isinstance(source, SourceType):
        return source.value
    return str(source).strip().upper()


def patent_id_value(record: object) -> str:
    """Return a normalized patent id for record-like objects."""
    return str(getattr(record, "patent_id", "")).strip()


def primary_authority_label(record: object) -> str:
    """Return a compact authority label for filters and cards."""
    authority = format_patent_authority(record)
    if authority == UNKNOWN_AUTHORITY_LABEL:
        return UNKNOWN_LABEL
    return authority


def patent_display_label(record: PatentRecord) -> str:
    """Return a short patent display label."""
    return f"{record.patent_id} ({format_patent_authority(record)})"


def display_value(value: Any) -> str:
    """Return a compact display value with an N/A fallback."""
    if value is None:
        return "N/A"
    text = str(value).strip()
    return text if text else "N/A"


def shorten(value: str | None, limit: int = 180) -> str:
    """Return a single-line preview of longer text values."""
    text = " ".join((value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def record_year(record: PatentRecord) -> str | None:
    """Extract the most relevant year from a patent record."""
    return _extract_year(record.publication_date) or _extract_year(record.filing_date)


def relationship_strength_label(score: float | None) -> str:
    """Convert a raw relationship score into a plain-language label."""
    if score is None:
        return "Weak"
    bounded_score = max(0.0, min(1.0, float(score)))
    if bounded_score >= 0.75:
        return "Strong"
    if bounded_score >= 0.50:
        return "Moderate"
    if bounded_score >= 0.25:
        return "Light"
    return "Weak"


def overlap_signal_label(score: float | None) -> str:
    """Convert a raw overlap score into a High/Medium/Low label."""
    if score is None:
        return "Low"
    bounded_score = max(0.0, min(100.0, float(score)))
    if bounded_score >= 75:
        return "High"
    if bounded_score >= 50:
        return "Medium"
    return "Low"


def grouping_quality_label(score: float | None) -> str:
    """Convert a raw grouping-quality score into a plain-language label."""
    if score is None:
        return "Not available"
    if score >= 0.50:
        return "Strong"
    if score >= 0.25:
        return "Moderate"
    return "Weak"


def keyword_importance_label(weight: float | None) -> str:
    """Convert a keyword-evidence weight into a plain-language label."""
    if weight is None:
        return "Supporting"
    bounded_weight = max(0.0, min(1.0, float(weight)))
    if bounded_weight >= 0.35:
        return "Very important"
    if bounded_weight >= 0.15:
        return "Important"
    return "Supporting"


def evidence_level_label(score: float | None) -> str:
    """Convert an application-area evidence score into a readable label."""
    if score is None:
        return "Low"
    bounded_score = max(0.0, min(100.0, float(score)))
    if bounded_score >= 60:
        return "High"
    if bounded_score >= 25:
        return "Medium"
    return "Low"


def technology_group_label(group_id: int | None) -> str:
    """Return a one-based display label for a technology group."""
    if group_id is None:
        return "Ungrouped"
    return f"Technology Group {int(group_id) + 1}"


INDIVIDUAL_ASSIGNEE_LABEL = "Individual inventors"


def display_assignee_label(value: str) -> str:
    """Return the display label for an assignee value.

    Curated corpus rows use the placeholder "Individual" for patents without a
    corporate assignee; presenting that as an organization name misreads as a
    company called "Individual" in Top players charts. Display-layer rename
    only — stored records keep the raw value.
    """
    if value.strip().casefold() == "individual":
        return INDIVIDUAL_ASSIGNEE_LABEL
    return value


def build_case_canonical_map(values: list[str]) -> dict[str, str]:
    """Map each label to one shared display form across its case variants.

    Curated corpus values mix casings such as "Smart garments" and
    "smart garments", which otherwise render as duplicate chart bars and
    duplicate filter options. Variants that differ only by letter case merge
    onto the most frequent original casing (ties break alphabetically), with
    the first letter capitalized. Display-layer only — records are untouched.
    """
    variants_by_key: dict[str, Counter[str]] = {}
    for value in values:
        variants_by_key.setdefault(value.casefold(), Counter())[value] += 1
    mapping: dict[str, str] = {}
    for variants in variants_by_key.values():
        display = min(variants.items(), key=lambda item: (-item[1], item[0]))[0]
        if display[:1].islower():
            display = display[:1].upper() + display[1:]
        for variant in variants:
            mapping[variant] = display
    return mapping


def source_authority_counts(records: list[PatentRecord]) -> dict[str, int]:
    """Return patent counts grouped by display authority."""
    return _sorted_count_mapping(
        Counter(format_patent_authority(record) for record in records)
    )


def import_method_counts(records: list[PatentRecord]) -> dict[str, int]:
    """Return patent counts grouped by display import method."""
    return _sorted_count_mapping(
        Counter(format_import_method(record) for record in records)
    )


def known_count(counts: dict[str, int]) -> int:
    """Return the number of non-unknown labels in a count mapping."""
    return len([label for label in counts if label != UNKNOWN_LABEL])


def year_range_from_counts(year_counts: dict[str, int]) -> str:
    """Return a readable year range from insight year counts."""
    years = [int(year) for year in year_counts if year != UNKNOWN_LABEL]
    if not years:
        return "N/A"
    minimum_year = min(years)
    maximum_year = max(years)
    if minimum_year == maximum_year:
        return str(minimum_year)
    return f"{minimum_year}-{maximum_year}"


def _extract_year(value: str | None) -> str | None:
    if value is None:
        return None
    match = _YEAR_PATTERN.search(str(value))
    return None if match is None else match.group(0)


def _sorted_count_mapping(counts: Counter[str]) -> dict[str, int]:
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
