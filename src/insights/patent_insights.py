"""Basic dataset-level insight generation for patent records."""

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.models.patent import PatentRecord

UNKNOWN_LABEL = "Unknown"
_YEAR_PATTERN = re.compile(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)")
_MISSING_METADATA_FIELDS = ("assignee", "year", "abstract", "country", "keywords")


@dataclass(slots=True)
class PatentInsightSummary:
    """Simple aggregate counts for a patent dataset."""

    total_patents: int
    source_counts: dict[str, int] = field(default_factory=dict)
    assignee_counts: dict[str, int] = field(default_factory=dict)
    year_counts: dict[str, int] = field(default_factory=dict)
    country_counts: dict[str, int] = field(default_factory=dict)
    top_keywords: dict[str, int] = field(default_factory=dict)
    missing_metadata_counts: dict[str, int] = field(default_factory=dict)
    cluster_distribution: dict[int, int] = field(default_factory=dict)


class PatentInsightsService:
    """Compute simple validation-friendly insights for patent datasets."""

    def summarize(
        self,
        records: list[PatentRecord],
        *,
        cluster_assignments: Mapping[str, int] | None = None,
        top_keyword_limit: int = 10,
    ) -> PatentInsightSummary:
        """Return aggregate counts for the provided patent records."""
        source_counts: Counter[str] = Counter()
        assignee_counts: Counter[str] = Counter()
        year_counts: Counter[str] = Counter()
        country_counts: Counter[str] = Counter()
        keyword_counts: Counter[str] = Counter()
        missing_metadata_counts: Counter[str] = Counter()

        for record in records:
            source_counts[_clean_text(record.source.value) or UNKNOWN_LABEL] += 1

            assignee = _clean_text(record.assignee)
            if assignee:
                assignee_counts[assignee] += 1
            else:
                assignee_counts[UNKNOWN_LABEL] += 1
                missing_metadata_counts["assignee"] += 1

            year = self._record_year(record)
            if year:
                year_counts[year] += 1
            else:
                year_counts[UNKNOWN_LABEL] += 1
                missing_metadata_counts["year"] += 1

            country = _clean_text(record.country)
            if country:
                country_counts[country] += 1
            else:
                missing_metadata_counts["country"] += 1

            if not _clean_text(record.abstract):
                missing_metadata_counts["abstract"] += 1

            keywords = [_clean_keyword(keyword) for keyword in record.keywords]
            keywords = [keyword for keyword in keywords if keyword]
            if keywords:
                keyword_counts.update(keywords)
            else:
                missing_metadata_counts["keywords"] += 1

        return PatentInsightSummary(
            total_patents=len(records),
            source_counts=_sorted_counts(source_counts),
            assignee_counts=_sorted_counts(assignee_counts),
            year_counts=self._sorted_year_counts(year_counts),
            country_counts=_sorted_counts(country_counts),
            top_keywords=_top_counts(keyword_counts, top_keyword_limit),
            missing_metadata_counts=_missing_metadata_summary(missing_metadata_counts),
            cluster_distribution=self._cluster_distribution(
                records, cluster_assignments
            ),
        )

    def _record_year(self, record: PatentRecord) -> str | None:
        publication_year = self._extract_year(record.publication_date)
        if publication_year:
            return publication_year
        return self._extract_year(record.filing_date)

    def _extract_year(self, value: Any) -> str | None:
        if value is None:
            return None

        text = _clean_text(value)
        if not text:
            return None

        match = _YEAR_PATTERN.search(text)
        return match.group(0) if match else None

    def _sorted_year_counts(self, counts: Counter[str]) -> dict[str, int]:
        def sort_key(item: tuple[str, int]) -> tuple[int, int, str]:
            year, count = item
            if year == UNKNOWN_LABEL:
                return (1, 0, year)
            return (0, int(year), year)

        return dict(sorted(counts.items(), key=sort_key))

    def _cluster_distribution(
        self,
        records: list[PatentRecord],
        cluster_assignments: Mapping[str, int] | None,
    ) -> dict[int, int]:
        if not cluster_assignments:
            return {}

        record_ids = {record.analysis_id for record in records}
        counts: Counter[int] = Counter()
        for analysis_id, cluster_id in cluster_assignments.items():
            if analysis_id in record_ids:
                counts[int(cluster_id)] += 1

        return dict(sorted(counts.items()))


def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "nan"}:
        return ""
    return " ".join(text.split())


def _clean_keyword(value: Any) -> str:
    return _clean_text(value).lower()


def _sorted_counts(counts: Counter[str]) -> dict[str, int]:
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _top_counts(counts: Counter[str], limit: int) -> dict[str, int]:
    if limit <= 0:
        return {}
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit])


def _missing_metadata_summary(counts: Counter[str]) -> dict[str, int]:
    return {field_name: counts[field_name] for field_name in _MISSING_METADATA_FIELDS}
