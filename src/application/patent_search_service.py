"""Application service for patent search, filtering, and card assembly."""

import re
from dataclasses import dataclass

from src.application._formatting import (
    display_value,
    format_import_method,
    primary_authority_label,
    record_year,
    shorten,
)
from src.application.dto import PatentCardDTO, PatentSearchResponseDTO
from src.insights import ApplicationAreaSuggestionService
from src.models.patent import PatentRecord

_SEARCH_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class RankedPatentResult:
    """Internal ranked patent result used before DTO conversion."""

    record: PatentRecord
    match_label: str
    score: int
    original_index: int


class PatentSearchService:
    """Build JSON-ready patent search responses without UI state."""

    def search(
        self,
        records: list[PatentRecord],
        *,
        query: str = "",
        source_filter: str = "All",
        assignee_filter: str = "All",
        country_filter: str = "All",
        year_filter: str = "All",
        limit: int | None = None,
    ) -> PatentSearchResponseDTO:
        """Filter, rank, and serialize patents as card DTOs."""
        filtered_patents = self.filter_patents(
            records,
            query=query,
            source_filter=source_filter,
            assignee_filter=assignee_filter,
            country_filter=country_filter,
            year_filter=year_filter,
        )
        ranked_results = self.rank_records(filtered_patents, query=query)
        visible_results = ranked_results
        if limit is not None:
            visible_results = ranked_results[: max(0, int(limit))]

        application_areas = self.application_area_names(
            [result.record for result in visible_results]
        )
        patents = [
            self.to_card(result, application_areas.get(result.record.analysis_id, []))
            for result in visible_results
        ]
        return PatentSearchResponseDTO(
            query=query.strip(),
            total_results=len(ranked_results),
            returned_results=len(patents),
            filters={
                "source": source_filter,
                "assignee": assignee_filter,
                "country": country_filter,
                "year": year_filter,
            },
            patents=patents,
        )

    def filter_patents(
        self,
        records: list[PatentRecord],
        *,
        query: str = "",
        source_filter: str = "All",
        assignee_filter: str = "All",
        country_filter: str = "All",
        year_filter: str = "All",
    ) -> list[PatentRecord]:
        """Return records that satisfy source, metadata, and search filters."""
        filtered: list[PatentRecord] = []
        for record in records:
            if (
                source_filter != "All"
                and primary_authority_label(record) != source_filter
            ):
                continue
            if assignee_filter != "All" and record.assignee != assignee_filter:
                continue
            if country_filter != "All" and record.country != country_filter:
                continue
            if year_filter != "All" and record_year(record) != year_filter:
                continue
            if query and not self.matches_search(record, query):
                continue
            filtered.append(record)

        return filtered

    def rank_records(
        self,
        records: list[PatentRecord],
        *,
        query: str = "",
    ) -> list[RankedPatentResult]:
        """Rank records by deterministic search score."""
        normalized_query = normalize_search_text(query)
        results: list[RankedPatentResult] = []
        for index, record in enumerate(records):
            score = self.search_score(record, normalized_query)
            results.append(
                RankedPatentResult(
                    record=record,
                    match_label=match_label(score, normalized_query),
                    score=score,
                    original_index=index,
                )
            )

        return sorted(
            results, key=lambda result: (-result.score, result.original_index)
        )

    def matches_search(self, record: PatentRecord, query: str) -> bool:
        """Return whether a patent contains all query evidence terms."""
        normalized_query = normalize_search_text(query)
        if not normalized_query:
            return True

        searchable_text = combined_search_text(record)
        if normalized_query in searchable_text:
            return True

        query_tokens = search_tokens(normalized_query)
        return bool(query_tokens) and all(
            token in searchable_text for token in query_tokens
        )

    def search_score(self, record: PatentRecord, query: str) -> int:
        """Return deterministic ranking score for a normalized query."""
        if not query:
            return 0

        score = 0
        query_tokens = search_tokens(query)
        patent_id = normalize_search_text(record.patent_id)
        title = normalize_search_text(record.title)
        keywords = normalize_search_text(" ".join(record.keywords))
        assignee = normalize_search_text(record.assignee or "")
        country = normalize_search_text(record.country or "")
        authority = normalize_search_text(primary_authority_label(record))
        abstract = normalize_search_text(record.abstract)

        if patent_id == query:
            score += 1000
        elif query in patent_id:
            score += 500

        if query in title:
            score += 330
        elif all_tokens_present(query_tokens, title):
            score += 260

        if any(normalize_search_text(keyword) == query for keyword in record.keywords):
            score += 320
        elif query in keywords:
            score += 280
        elif all_tokens_present(query_tokens, keywords):
            score += 230

        if query in assignee:
            score += 180
        elif all_tokens_present(query_tokens, assignee):
            score += 145

        if query in country or query in authority:
            score += 140

        if query in abstract:
            score += 85
        elif all_tokens_present(query_tokens, abstract):
            score += 65

        score += 8 * token_overlap(query_tokens, title)
        score += 7 * token_overlap(query_tokens, keywords)
        score += 5 * token_overlap(query_tokens, assignee)
        score += 2 * token_overlap(query_tokens, abstract)
        return score

    def to_card(
        self,
        result: RankedPatentResult,
        candidate_application_areas: list[str] | None = None,
    ) -> PatentCardDTO:
        """Serialize a ranked record as a patent card DTO."""
        record = result.record
        return PatentCardDTO(
            analysis_id=record.analysis_id,
            patent_id=record.patent_id,
            source=record.source.value,
            source_authority=primary_authority_label(record),
            import_method=format_import_method(record),
            title=record.title,
            abstract_preview=shorten(record.abstract, limit=360),
            assignee=display_value(record.assignee),
            country=display_value(record.country),
            year=record_year(record),
            keywords=[keyword for keyword in record.keywords if keyword],
            candidate_application_areas=candidate_application_areas or [],
            match_label=result.match_label,
            match_score=result.score,
            source_url=record.source_url,
        )

    def application_area_names(
        self,
        records: list[PatentRecord],
        *,
        limit: int = 3,
    ) -> dict[str, list[str]]:
        """Return top candidate application-area labels by patent analysis id."""
        if not records:
            return {}

        suggestions = ApplicationAreaSuggestionService().suggest_for_patents(records)
        return {
            result.analysis_id: [
                suggestion.area_name for suggestion in result.suggestions[:limit]
            ]
            for result in suggestions
            if result.suggestions
        }


def combined_search_text(record: PatentRecord) -> str:
    """Return normalized text used by search matching."""
    return normalize_search_text(
        " ".join(
            [
                record.patent_id,
                record.title,
                record.abstract,
                record.assignee or "",
                record.country or "",
                primary_authority_label(record),
                " ".join(record.keywords),
            ]
        )
    )


def match_label(score: int, query: str) -> str:
    """Return a readable match label from score and query state."""
    if not query:
        return "Curated record"
    if score >= 500:
        return "Best match"
    if score >= 225:
        return "Strong match"
    return "Related match"


def normalize_search_text(value: str | None) -> str:
    """Normalize user search text into simple lowercase tokens."""
    if value is None:
        return ""
    return " ".join(_SEARCH_TOKEN_PATTERN.findall(str(value).lower()))


def search_tokens(query: str) -> list[str]:
    """Split normalized query text into tokens."""
    return [token for token in query.split() if token]


def all_tokens_present(tokens: list[str], text: str) -> bool:
    """Return whether all tokens appear in text."""
    return bool(tokens) and all(token in text for token in tokens)


def token_overlap(tokens: list[str], text: str) -> int:
    """Return count of query tokens appearing in text."""
    return sum(1 for token in tokens if token in text)
