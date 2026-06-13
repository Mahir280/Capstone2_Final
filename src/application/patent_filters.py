"""Shared patent filtering and filter metadata helpers."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from src.application._formatting import build_case_canonical_map
from src.models.enums import SourceType
from src.models.patent import PatentRecord

ALLOWED_LANDSCAPE_SOURCES = frozenset(
    {
        SourceType.USPTO.value,
        SourceType.EPO.value,
        SourceType.TURKPATENT.value,
    }
)
FILTER_METADATA_LIMIT = 30
_YEAR_PATTERN = re.compile(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)")
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_CLASSIFICATION_PREFIX_PATTERN = re.compile(r"^[A-Z]\d{2}[A-Z]?")


@dataclass(frozen=True, slots=True)
class PatentFilterParams:
    """Normalized patent filter values for landscape generation."""

    sources: tuple[str, ...] = field(default_factory=tuple)
    publication_year_from: int | None = None
    publication_year_to: int | None = None
    filing_year_from: int | None = None
    filing_year_to: int | None = None
    countries: tuple[str, ...] = field(default_factory=tuple)
    assignee: str | None = None
    keyword: str | None = None
    application_area: str | None = None
    classification: str | None = None

    @classmethod
    def from_query(
        cls,
        *,
        source: list[str] | None = None,
        publication_year_from: int | None = None,
        publication_year_to: int | None = None,
        filing_year_from: int | None = None,
        filing_year_to: int | None = None,
        country: list[str] | None = None,
        assignee: str | None = None,
        keyword: str | None = None,
        application_area: str | None = None,
        classification: str | None = None,
    ) -> "PatentFilterParams":
        """Build and validate normalized filters from raw query params."""
        sources = _multi_value(source, uppercase=True)
        invalid_sources = [
            value for value in sources if value not in ALLOWED_LANDSCAPE_SOURCES
        ]
        if invalid_sources:
            allowed = ", ".join(sorted(ALLOWED_LANDSCAPE_SOURCES))
            invalid = ", ".join(invalid_sources)
            raise ValueError(f"Invalid source value(s): {invalid}. Allowed: {allowed}.")

        _validate_year_range(
            publication_year_from,
            publication_year_to,
            "publication_year",
        )
        _validate_year_range(filing_year_from, filing_year_to, "filing_year")

        return cls(
            sources=sources,
            publication_year_from=publication_year_from,
            publication_year_to=publication_year_to,
            filing_year_from=filing_year_from,
            filing_year_to=filing_year_to,
            countries=_multi_value(country, uppercase=True),
            assignee=_clean_filter_text(assignee),
            keyword=_clean_filter_text(keyword),
            application_area=_clean_filter_text(application_area),
            classification=_clean_filter_text(classification),
        )

    @property
    def has_filters(self) -> bool:
        """Return whether any filtering input is active."""
        return bool(self.active_filters())

    def active_filters(self) -> dict[str, Any]:
        """Return a JSON-ready mapping of active filters."""
        active: dict[str, Any] = {}
        if self.sources:
            active["source"] = list(self.sources)
        if self.publication_year_from is not None:
            active["publication_year_from"] = self.publication_year_from
        if self.publication_year_to is not None:
            active["publication_year_to"] = self.publication_year_to
        if self.filing_year_from is not None:
            active["filing_year_from"] = self.filing_year_from
        if self.filing_year_to is not None:
            active["filing_year_to"] = self.filing_year_to
        if self.countries:
            active["country"] = list(self.countries)
        if self.assignee:
            active["assignee"] = self.assignee
        if self.keyword:
            active["keyword"] = self.keyword
        if self.application_area:
            active["application_area"] = self.application_area
        if self.classification:
            active["classification"] = self.classification
        return active


def apply_patent_filters(
    records: list[PatentRecord],
    filters: PatentFilterParams,
) -> list[PatentRecord]:
    """Return records that satisfy the provided filter params."""
    if not filters.has_filters:
        return list(records)

    filtered: list[PatentRecord] = []
    for record in records:
        if filters.sources and record.source.value.upper() not in filters.sources:
            continue
        if not _matches_year_range(
            record.publication_date,
            filters.publication_year_from,
            filters.publication_year_to,
        ):
            continue
        if not _matches_year_range(
            record.filing_date,
            filters.filing_year_from,
            filters.filing_year_to,
        ):
            continue
        if filters.countries and _normalized_upper(record.country) not in (
            filters.countries
        ):
            continue
        if filters.assignee and not _contains_text(record.assignee, filters.assignee):
            continue
        if filters.keyword and not _matches_keyword(record, filters.keyword):
            continue
        if filters.application_area and not _matches_application_area(
            record,
            filters.application_area,
        ):
            continue
        if filters.classification and not _matches_classification(
            record,
            filters.classification,
        ):
            continue
        filtered.append(record)

    return filtered


def ensure_focus_record_included(
    records: list[PatentRecord],
    filtered_records: list[PatentRecord],
    selected_analysis_id: str,
) -> tuple[list[PatentRecord], bool]:
    """Include the requested focus record even if filters would hide it."""
    filtered_ids = {record.analysis_id for record in filtered_records}
    if selected_analysis_id in filtered_ids:
        return filtered_records, False

    focus_record = next(
        (record for record in records if record.analysis_id == selected_analysis_id),
        None,
    )
    if focus_record is None:
        return filtered_records, False

    return [focus_record, *filtered_records], True


def filter_warnings(
    filters: PatentFilterParams,
    filtered_count: int,
    *,
    focus_record_added: bool = False,
) -> list[str]:
    """Return user-facing warnings for sparse filtered landscapes."""
    warnings: list[str] = []
    if not filters.has_filters:
        return warnings

    if filtered_count == 0 and focus_record_added:
        warnings.append(
            "The active patent filters matched no records beyond the focused patent; "
            "the focused landscape may be sparse."
        )
    elif filtered_count == 0:
        warnings.append(
            "The active patent filters matched no records; no landscape graph was "
            "generated."
        )
    elif filtered_count < 2:
        warnings.append(
            "The active patent filters matched fewer than 2 records; relationship "
            "mapping may be sparse."
        )

    if focus_record_added:
        warnings.append(
            "The focused patent was added to the filtered landscape so the requested "
            "focus remains visible."
        )
    return warnings


def build_filter_metadata(records: list[PatentRecord]) -> dict[str, Any]:
    """Return available filter options and lightweight counts."""
    source_counts = _sorted_counts(
        Counter(record.source.value for record in records if record.source.value)
    )
    country_counts = _sorted_counts(
        Counter(_clean_display_text(record.country) for record in records)
    )
    assignee_counts = _sorted_counts(
        Counter(_clean_display_text(record.assignee) for record in records)
    )
    keyword_counts = _sorted_counts(
        Counter(
            keyword
            for record in records
            for keyword in (_clean_display_text(value) for value in record.keywords)
            if keyword
        )
    )
    # Merge case-variant area labels (e.g. "Smart garments" / "smart garments")
    # into one option; area filtering matches case-insensitively, so a merged
    # display label still reaches every underlying record.
    raw_areas = [
        area
        for record in records
        for area in (
            _clean_display_text(value) for value in record.candidate_application_areas
        )
        if area
    ]
    area_display = build_case_canonical_map(raw_areas)
    application_area_counts = _sorted_counts(
        Counter(area_display.get(area, area) for area in raw_areas)
    )
    classification_counts = _sorted_counts(
        Counter(
            prefix
            for record in records
            for prefix in _classification_prefixes(record)
            if prefix
        )
    )
    publication_years = _years(record.publication_date for record in records)
    filing_years = _years(record.filing_date for record in records)
    display_years = _years(
        record.publication_date or record.filing_date for record in records
    )

    return {
        "sources": sorted(source_counts),
        "source_counts": source_counts,
        "countries": sorted(country_counts),
        "country_counts": country_counts,
        "years": [str(year) for year in display_years],
        "publication_year_range": _year_range(publication_years),
        "filing_year_range": _year_range(filing_years),
        "assignees": sorted(assignee_counts),
        "top_assignees": _limited_counts(assignee_counts),
        "top_keywords": _limited_counts(keyword_counts),
        "candidate_application_areas": sorted(application_area_counts),
        "top_application_areas": _limited_counts(application_area_counts),
        "classifications": list(_limited_counts(classification_counts)),
        "top_classifications": _limited_counts(classification_counts),
        "technology_groups": [],
    }


def _multi_value(
    values: list[str] | None, *, uppercase: bool = False
) -> tuple[str, ...]:
    if values is None:
        return ()

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        for part in str(value).split(","):
            text = part.strip()
            if not text or text.lower() == "all":
                continue
            if uppercase:
                text = text.upper()
            if text in seen:
                continue
            seen.add(text)
            cleaned.append(text)
    return tuple(cleaned)


def _validate_year_range(
    year_from: int | None,
    year_to: int | None,
    label: str,
) -> None:
    if year_from is not None and year_to is not None and year_from > year_to:
        raise ValueError(f"{label}_from must be less than or equal to {label}_to.")


def _matches_year_range(
    raw_date: str | None,
    year_from: int | None,
    year_to: int | None,
) -> bool:
    if year_from is None and year_to is None:
        return True

    year = _extract_year(raw_date)
    if year is None:
        return False
    if year_from is not None and year < year_from:
        return False
    if year_to is not None and year > year_to:
        return False
    return True


def _extract_year(value: str | None) -> int | None:
    if value is None:
        return None
    match = _YEAR_PATTERN.search(str(value))
    return None if match is None else int(match.group(0))


def _matches_keyword(record: PatentRecord, keyword: str) -> bool:
    return _matches_text_query(
        " ".join([record.title, record.abstract, " ".join(record.keywords)]),
        keyword,
    )


def _matches_application_area(record: PatentRecord, application_area: str) -> bool:
    return _matches_text_query(
        " ".join(record.candidate_application_areas),
        application_area,
    )


def _matches_classification(record: PatentRecord, classification: str) -> bool:
    query = classification.casefold()
    if not query:
        return True
    return any(
        query in code.casefold()
        for code in [*record.ipc_codes, *record.cpc_codes]
        if code
    )


def _contains_text(value: str | None, query: str) -> bool:
    if value is None:
        return False
    return query.casefold() in value.casefold()


def _matches_text_query(text: str, query: str) -> bool:
    normalized_text = _normalize_text(text)
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return True
    if normalized_query in normalized_text:
        return True
    tokens = _search_tokens(normalized_query)
    return bool(tokens) and all(token in normalized_text for token in tokens)


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(_TOKEN_PATTERN.findall(str(value).casefold()))


def _search_tokens(query: str) -> list[str]:
    return [token for token in query.split() if token]


def _clean_filter_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "all":
        return None
    return text


def _normalized_upper(value: str | None) -> str:
    return str(value or "").strip().upper()


def _clean_display_text(value: str | None) -> str:
    return str(value or "").strip()


def _years(values: object) -> list[int]:
    years = sorted(
        {
            year
            for value in values
            if (year := _extract_year(str(value) if value else None)) is not None
        }
    )
    return years


def _year_range(years: list[int]) -> dict[str, int | None]:
    if not years:
        return {"min": None, "max": None}
    return {"min": min(years), "max": max(years)}


def _classification_prefixes(record: PatentRecord) -> list[str]:
    prefixes: list[str] = []
    seen: set[str] = set()
    for code in [*record.ipc_codes, *record.cpc_codes]:
        text = str(code or "").strip().upper().replace(" ", "")
        if not text:
            continue
        match = _CLASSIFICATION_PREFIX_PATTERN.search(text)
        prefix = match.group(0) if match is not None else text
        if prefix in seen:
            continue
        seen.add(prefix)
        prefixes.append(prefix)
    return prefixes


def _sorted_counts(counts: Counter[str]) -> dict[str, int]:
    cleaned = Counter({key: count for key, count in counts.items() if key})
    return dict(sorted(cleaned.items(), key=lambda item: (-item[1], item[0])))


def _limited_counts(counts: dict[str, int]) -> dict[str, int]:
    return dict(list(counts.items())[:FILTER_METADATA_LIMIT])
