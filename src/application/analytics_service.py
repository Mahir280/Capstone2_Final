"""Application service for filter-aware visual analytics DTOs.

Computes cheap O(n) aggregates over an already-filtered patent corpus for the
visual analytics dashboard: corpus composition, time trends, assignee
breakdowns, technology distributions, and data-quality metrics. Filtering is
handled upstream by :mod:`src.application.patent_filters`; this service only
summarizes the records it is given.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from src.application._formatting import (
    UNKNOWN_LABEL,
    build_case_canonical_map,
    display_assignee_label,
    format_patent_authority,
)
from src.application.patent_filters import _classification_prefixes
from src.models.patent import PatentRecord

TOP_ASSIGNEES = 15
TOP_KEYWORDS = 20
TOP_APPLICATION_AREAS = 20
TOP_CLASSIFICATIONS = 20
TOP_COOCCURRENCE_KEYWORDS = 15

_YEAR_PATTERN = re.compile(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)")

# Fields tracked for data-quality completeness. The boolean reports presence.
_QUALITY_FIELDS: tuple[str, ...] = (
    "assignee",
    "country",
    "publication_date",
    "filing_date",
    "abstract",
    "keywords",
    "ipc_codes",
    "cpc_codes",
    "application_areas",
)


@dataclass(slots=True)
class CorpusAnalytics:
    """Corpus-composition aggregates."""

    by_source: dict[str, int] = field(default_factory=dict)
    by_country: dict[str, int] = field(default_factory=dict)
    source_country: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass(slots=True)
class TrendAnalytics:
    """Time-trend aggregates keyed by year."""

    by_publication_year: dict[str, int] = field(default_factory=dict)
    by_filing_year: dict[str, int] = field(default_factory=dict)
    source_by_year: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass(slots=True)
class AssigneeAnalytics:
    """Assignee aggregates restricted to the top assignees."""

    top: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, dict[str, int]] = field(default_factory=dict)
    by_application_area: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass(slots=True)
class TechnologyAnalytics:
    """Technology aggregates: keywords, application areas, classifications."""

    top_keywords: dict[str, int] = field(default_factory=dict)
    application_areas: dict[str, int] = field(default_factory=dict)
    classifications: dict[str, int] = field(default_factory=dict)
    keyword_application_area: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass(slots=True)
class QualityAnalytics:
    """Data-quality completeness metrics."""

    missing_by_field: dict[str, int] = field(default_factory=dict)
    field_completeness_pct: dict[str, float] = field(default_factory=dict)
    completeness_score: float = 0.0


@dataclass(slots=True)
class AnalyticsDTO:
    """Bundled analytics sections for the visual analytics dashboard."""

    corpus: CorpusAnalytics
    trends: TrendAnalytics
    assignees: AssigneeAnalytics
    technology: TechnologyAnalytics
    quality: QualityAnalytics


class AnalyticsService:
    """Assemble JSON-ready visual analytics from a filtered patent corpus."""

    def build_analytics(self, records: list[PatentRecord]) -> AnalyticsDTO:
        """Return analytics sections for the provided (already filtered) records."""
        area_display = _area_display_map(records)
        return AnalyticsDTO(
            corpus=self._corpus(records),
            trends=self._trends(records),
            assignees=self._assignees(records, area_display),
            technology=self._technology(records, area_display),
            quality=self._quality(records),
        )

    def _corpus(self, records: list[PatentRecord]) -> CorpusAnalytics:
        by_source: Counter[str] = Counter()
        by_country: Counter[str] = Counter()
        source_country: dict[str, Counter[str]] = {}
        for record in records:
            authority = format_patent_authority(record)
            country = _country_label(record)
            by_source[authority] += 1
            by_country[country] += 1
            source_country.setdefault(authority, Counter())[country] += 1
        return CorpusAnalytics(
            by_source=_sorted_counts(by_source),
            by_country=_sorted_counts(by_country),
            source_country=_sorted_nested(source_country),
        )

    def _trends(self, records: list[PatentRecord]) -> TrendAnalytics:
        by_publication_year: Counter[str] = Counter()
        by_filing_year: Counter[str] = Counter()
        source_by_year: dict[str, Counter[str]] = {}
        for record in records:
            publication_year = _extract_year(record.publication_date)
            filing_year = _extract_year(record.filing_date)
            if publication_year is not None:
                by_publication_year[publication_year] += 1
            if filing_year is not None:
                by_filing_year[filing_year] += 1
            display_year = publication_year or filing_year
            if display_year is not None:
                authority = format_patent_authority(record)
                source_by_year.setdefault(display_year, Counter())[authority] += 1
        return TrendAnalytics(
            by_publication_year=_sorted_by_key(by_publication_year),
            by_filing_year=_sorted_by_key(by_filing_year),
            source_by_year=_nested_sorted_by_key(source_by_year),
        )

    def _assignees(
        self,
        records: list[PatentRecord],
        area_display: dict[str, str],
    ) -> AssigneeAnalytics:
        assignee_counts: Counter[str] = Counter()
        for record in records:
            assignee = _display_assignee(record)
            if assignee:
                assignee_counts[assignee] += 1
        top = _limited(_sorted_counts(assignee_counts), TOP_ASSIGNEES)
        top_names = set(top)

        by_source: dict[str, Counter[str]] = {}
        by_application_area: dict[str, Counter[str]] = {}
        for record in records:
            assignee = _display_assignee(record)
            if not assignee or assignee not in top_names:
                continue
            authority = format_patent_authority(record)
            by_source.setdefault(assignee, Counter())[authority] += 1
            for area in _display_areas(record, area_display):
                by_application_area.setdefault(assignee, Counter())[area] += 1
        return AssigneeAnalytics(
            top=top,
            by_source=_sorted_nested(by_source),
            by_application_area=_sorted_nested(by_application_area),
        )

    def _technology(
        self,
        records: list[PatentRecord],
        area_display: dict[str, str],
    ) -> TechnologyAnalytics:
        keyword_counts: Counter[str] = Counter()
        area_counts: Counter[str] = Counter()
        classification_counts: Counter[str] = Counter()
        for record in records:
            keyword_counts.update(_clean_values(record.keywords))
            area_counts.update(_display_areas(record, area_display))
            classification_counts.update(_classification_prefixes(record))

        top_keywords = _limited(_sorted_counts(keyword_counts), TOP_KEYWORDS)
        cooccurrence_keywords = list(top_keywords)[:TOP_COOCCURRENCE_KEYWORDS]
        keyword_application_area = self._keyword_area_cooccurrence(
            records,
            cooccurrence_keywords,
            area_display,
        )
        return TechnologyAnalytics(
            top_keywords=top_keywords,
            application_areas=_limited(
                _sorted_counts(area_counts),
                TOP_APPLICATION_AREAS,
            ),
            classifications=_limited(
                _sorted_counts(classification_counts),
                TOP_CLASSIFICATIONS,
            ),
            keyword_application_area=keyword_application_area,
        )

    def _keyword_area_cooccurrence(
        self,
        records: list[PatentRecord],
        keywords: list[str],
        area_display: dict[str, str],
    ) -> dict[str, dict[str, int]]:
        if not keywords:
            return {}
        lowered = {keyword: keyword.casefold() for keyword in keywords}
        cooccurrence: dict[str, Counter[str]] = {}
        for record in records:
            record_keywords = {
                value.casefold() for value in _clean_values(record.keywords)
            }
            areas = _display_areas(record, area_display)
            if not areas:
                continue
            for keyword, lowered_keyword in lowered.items():
                if lowered_keyword in record_keywords:
                    bucket = cooccurrence.setdefault(keyword, Counter())
                    bucket.update(areas)
        return _sorted_nested(cooccurrence)

    def _quality(self, records: list[PatentRecord]) -> QualityAnalytics:
        total = len(records)
        present_counts = dict.fromkeys(_QUALITY_FIELDS, 0)
        for record in records:
            for field_name in _QUALITY_FIELDS:
                if _field_present(record, field_name):
                    present_counts[field_name] += 1

        missing_by_field: dict[str, int] = {}
        field_completeness_pct: dict[str, float] = {}
        for field_name in _QUALITY_FIELDS:
            present = present_counts[field_name]
            missing_by_field[field_name] = total - present
            field_completeness_pct[field_name] = (
                round(present / total * 100, 1) if total else 0.0
            )

        if total and _QUALITY_FIELDS:
            completeness_score = round(
                sum(present_counts[name] for name in _QUALITY_FIELDS)
                / (total * len(_QUALITY_FIELDS)),
                4,
            )
        else:
            completeness_score = 0.0

        return QualityAnalytics(
            missing_by_field=missing_by_field,
            field_completeness_pct=field_completeness_pct,
            completeness_score=completeness_score,
        )


def _field_present(record: PatentRecord, field_name: str) -> bool:
    if field_name == "application_areas":
        return bool(record.candidate_application_areas)
    value = getattr(record, field_name, None)
    if isinstance(value, list):
        return bool(value)
    return bool(_clean(value))


def _country_label(record: PatentRecord) -> str:
    return _clean(record.country) or UNKNOWN_LABEL


def _clean(value: str | None) -> str:
    return str(value or "").strip()


def _display_assignee(record: PatentRecord) -> str:
    return display_assignee_label(_clean(record.assignee))


def _area_display_map(records: list[PatentRecord]) -> dict[str, str]:
    """Build one shared case-insensitive display mapping for area labels."""
    return build_case_canonical_map(
        [
            area
            for record in records
            for area in _clean_values(record.candidate_application_areas)
        ]
    )


def _display_areas(
    record: PatentRecord,
    area_display: dict[str, str],
) -> list[str]:
    return [
        area_display.get(area, area)
        for area in _clean_values(record.candidate_application_areas)
    ]


def _clean_values(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = _clean(value)
        if text:
            cleaned.append(text)
    return cleaned


def _extract_year(value: str | None) -> str | None:
    if value is None:
        return None
    match = _YEAR_PATTERN.search(str(value))
    return None if match is None else match.group(0)


def _sorted_counts(counts: Counter[str]) -> dict[str, int]:
    cleaned = {key: count for key, count in counts.items() if key}
    return dict(sorted(cleaned.items(), key=lambda item: (-item[1], item[0])))


def _sorted_nested(counts: dict[str, Counter[str]]) -> dict[str, dict[str, int]]:
    return {
        key: _sorted_counts(inner)
        for key, inner in sorted(
            counts.items(),
            key=lambda item: (-sum(item[1].values()), item[0]),
        )
    }


def _sorted_by_key(counts: Counter[str]) -> dict[str, int]:
    cleaned = {key: count for key, count in counts.items() if key}
    return dict(sorted(cleaned.items(), key=lambda item: item[0]))


def _nested_sorted_by_key(
    counts: dict[str, Counter[str]],
) -> dict[str, dict[str, int]]:
    return {key: _sorted_counts(counts[key]) for key in sorted(counts)}


def _limited(counts: dict[str, int], limit: int) -> dict[str, int]:
    return dict(list(counts.items())[:limit])
