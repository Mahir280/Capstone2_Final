"""Application service for patent profiles and related-patent discovery."""

from typing import Any

from src.application._formatting import (
    display_value,
    evidence_level_label,
    format_import_method,
    format_patent_authority,
    keyword_importance_label,
    overlap_signal_label,
    primary_authority_label,
    record_year,
    relationship_strength_label,
    shorten,
    technology_group_label,
)
from src.application.dto import PatentProfileDTO, RelatedPatentDTO
from src.clustering.kmeans_clusterer import KMeansPatentClusterer
from src.clustering.similarity_mapper import TfidfSimilarityMapper
from src.features.tfidf import TfidfFeatureResult, TfidfFeatureService
from src.insights import (
    ApplicationAreaSuggestion,
    ApplicationAreaSuggestionService,
    OverlapRiskService,
    OverlapRiskSignal,
)
from src.models.patent import PatentRecord


class PatentProfileService:
    """Assemble patent profiles and related-patent DTOs without UI objects."""

    def __init__(
        self,
        *,
        tfidf_service: TfidfFeatureService | None = None,
        application_service: ApplicationAreaSuggestionService | None = None,
        clusterer: KMeansPatentClusterer | None = None,
        similarity_mapper: TfidfSimilarityMapper | None = None,
        overlap_service: OverlapRiskService | None = None,
    ) -> None:
        self.tfidf_service = tfidf_service or TfidfFeatureService()
        self.application_service = (
            application_service or ApplicationAreaSuggestionService()
        )
        self.clusterer = clusterer or KMeansPatentClusterer()
        self.similarity_mapper = similarity_mapper or TfidfSimilarityMapper()
        self.overlap_service = overlap_service or OverlapRiskService()

    def get_profile(
        self,
        records: list[PatentRecord],
        analysis_id: str,
        *,
        tfidf_result: TfidfFeatureResult | None = None,
        include_related: bool = False,
        relationship_threshold: float = 0.20,
        top_k: int = 5,
        technology_group_count: int = 7,
        top_terms_limit: int = 10,
    ) -> PatentProfileDTO | None:
        """Return a full profile for the selected analysis id."""
        record = _record_by_analysis_id(records).get(analysis_id)
        if record is None:
            return None

        features = tfidf_result or self.tfidf_service.build_from_patents(records)
        application_result = self.application_service.suggest_for_patents([record])[0]
        warnings = list(application_result.warnings)
        top_terms = self._top_terms(features, analysis_id, top_terms_limit)
        related_patents: list[RelatedPatentDTO] = []
        if include_related:
            related_patents, related_warnings = self.get_related_patents(
                records,
                analysis_id,
                tfidf_result=features,
                relationship_threshold=relationship_threshold,
                top_k=top_k,
                technology_group_count=technology_group_count,
            )
            warnings.extend(related_warnings)

        return PatentProfileDTO(
            analysis_id=record.analysis_id,
            patent_id=record.patent_id,
            source=record.source.value,
            source_authority=format_patent_authority(record),
            import_method=format_import_method(record),
            title=record.title,
            abstract=record.abstract,
            plain_language_summary=self._summary_text(
                record,
                application_result.suggestions,
            ),
            assignee=record.assignee,
            inventors=list(record.inventors),
            publication_date=record.publication_date,
            filing_date=record.filing_date,
            year=record_year(record),
            country=record.country,
            language=record.language,
            source_url=record.source_url,
            keywords=list(record.keywords),
            ipc_codes=list(record.ipc_codes),
            cpc_codes=list(record.cpc_codes),
            claims_preview=(
                shorten(record.claims_text, limit=1600) if record.claims_text else None
            ),
            top_terms=top_terms,
            candidate_application_areas=[
                self._application_area_dict(suggestion)
                for suggestion in application_result.suggestions
            ],
            related_patents=related_patents,
            metadata_rows=self._metadata_rows(record),
            advanced_metadata_rows=self._advanced_metadata_rows(record),
            warnings=_dedupe(warnings),
        )

    def get_related_patents(
        self,
        records: list[PatentRecord],
        analysis_id: str,
        *,
        tfidf_result: TfidfFeatureResult | None = None,
        relationship_threshold: float = 0.20,
        top_k: int = 5,
        technology_group_count: int = 7,
    ) -> tuple[list[RelatedPatentDTO], list[str]]:
        """Return related-patent DTOs and safe warnings for one patent."""
        records_by_id = _record_by_analysis_id(records)
        selected_record = records_by_id.get(analysis_id)
        if selected_record is None:
            return [], [f"Patent analysis id '{analysis_id}' was not found."]
        if len(records) < 2:
            return [], ["At least 2 patents are required to find related patents."]

        features = tfidf_result or self.tfidf_service.build_from_patents(records)
        if not features.is_valid:
            message = features.error or "Keyword evidence is not available."
            return [], [message]

        cluster_result = self.clusterer.cluster(
            records,
            features,
            technology_group_count,
        )
        similarity_result = self.similarity_mapper.map_relationships(
            records,
            features,
            similarity_threshold=relationship_threshold,
            top_k=top_k,
        )
        overlap_result = self.overlap_service.evaluate(
            records,
            similarity_result,
            cluster_result.assignments,
            min_risk_score=0.0,
        )
        candidate_areas = self._candidate_area_names(records)
        related_signals = [
            signal
            for signal in overlap_result.signals
            if analysis_id in {signal.source_analysis_id, signal.target_analysis_id}
        ]
        related_patents = [
            self._related_patent_dto(
                signal,
                analysis_id,
                records_by_id,
                candidate_areas,
            )
            for signal in related_signals
            if self._other_analysis_id(analysis_id, signal) in records_by_id
        ]
        warnings = _dedupe(
            [
                *cluster_result.warnings,
                *similarity_result.warnings,
                *overlap_result.warnings,
            ]
        )
        return related_patents, warnings

    def _top_terms(
        self,
        tfidf_result: TfidfFeatureResult,
        analysis_id: str,
        top_terms_limit: int,
    ) -> list[dict[str, Any]]:
        terms = self.tfidf_service.top_terms_for_patent(
            tfidf_result,
            analysis_id,
            top_n=top_terms_limit,
        )
        return [
            {
                "term": term.term,
                "importance": keyword_importance_label(term.score),
                "score": round(term.score, 4),
            }
            for term in terms
        ]

    def _application_area_dict(
        self,
        suggestion: ApplicationAreaSuggestion,
    ) -> dict[str, Any]:
        return {
            "area_name": suggestion.area_name,
            "score": round(suggestion.score, 2),
            "evidence_level": evidence_level_label(suggestion.score),
            "matched_terms": list(suggestion.matched_terms),
            "evidence_count": suggestion.evidence_count,
            "explanation": suggestion.explanation,
        }

    def _related_patent_dto(
        self,
        signal: OverlapRiskSignal,
        selected_analysis_id: str,
        records_by_id: dict[str, PatentRecord],
        candidate_areas: dict[str, list[str]],
    ) -> RelatedPatentDTO:
        related_analysis_id = self._other_analysis_id(selected_analysis_id, signal)
        related_record = records_by_id[related_analysis_id]
        return RelatedPatentDTO(
            analysis_id=related_record.analysis_id,
            patent_id=related_record.patent_id,
            source=related_record.source.value,
            source_authority=primary_authority_label(related_record),
            title=related_record.title,
            assignee=related_record.assignee,
            country=related_record.country,
            year=record_year(related_record),
            relationship_strength=relationship_strength_label(signal.similarity_score),
            similarity_score=round(signal.similarity_score, 4),
            overlap_signal=overlap_signal_label(signal.risk_score),
            overlap_score=round(signal.risk_score, 2),
            same_technology_group=signal.shared_cluster,
            source_technology_group_id=signal.source_cluster_id,
            target_technology_group_id=signal.target_cluster_id,
            source_technology_group=technology_group_label(signal.source_cluster_id),
            target_technology_group=technology_group_label(signal.target_cluster_id),
            shared_keywords=list(signal.shared_keywords),
            candidate_application_areas=candidate_areas.get(
                related_record.analysis_id,
                [],
            ),
            explanation=signal.explanation,
        )

    def _candidate_area_names(
        self,
        records: list[PatentRecord],
    ) -> dict[str, list[str]]:
        results = self.application_service.suggest_for_patents(records)
        return {
            result.analysis_id: [
                suggestion.area_name for suggestion in result.suggestions[:3]
            ]
            for result in results
            if result.suggestions
        }

    def _summary_text(
        self,
        record: PatentRecord,
        suggestions: list[ApplicationAreaSuggestion],
    ) -> str:
        keyword_phrase = self._keyword_phrase(record)
        area_names = [suggestion.area_name for suggestion in suggestions[:3]]
        area_text = (
            self._human_join(area_names)
            if area_names
            else "smart textiles, flexible sensors, or wearable monitoring systems"
        )

        return (
            "Based on its stored title, abstract, and keywords, this patent appears "
            f"to describe {keyword_phrase}. It may be relevant to {area_text} as "
            "candidate application context within the current curated dataset."
        )

    def _keyword_phrase(self, record: PatentRecord) -> str:
        keywords = [keyword.strip().lower() for keyword in record.keywords if keyword]
        if keywords:
            return f"a {', '.join(keywords[:3])} technology"

        title = shorten(record.title, limit=90).lower()
        if title:
            return f"a technology related to {title}"
        return "a fiber-based wearable electronics technology"

    def _human_join(self, values: list[str]) -> str:
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} or {values[1]}"
        return f"{', '.join(values[:-1])}, or {values[-1]}"

    def _metadata_rows(self, record: PatentRecord) -> list[dict[str, str]]:
        return [
            {"Field": "Patent ID", "Value": record.patent_id},
            {"Field": "Source authority", "Value": format_patent_authority(record)},
            {"Field": "Imported via", "Value": format_import_method(record)},
            {"Field": "Assignee", "Value": display_value(record.assignee)},
            {"Field": "Country", "Value": display_value(record.country)},
            {
                "Field": "Publication date",
                "Value": display_value(record.publication_date),
            },
            {"Field": "Filing date", "Value": display_value(record.filing_date)},
            {"Field": "Language", "Value": display_value(record.language)},
            {"Field": "Inventors", "Value": display_value(", ".join(record.inventors))},
            {"Field": "IPC codes", "Value": display_value(", ".join(record.ipc_codes))},
            {"Field": "CPC codes", "Value": display_value(", ".join(record.cpc_codes))},
            {"Field": "Keywords", "Value": display_value(", ".join(record.keywords))},
        ]

    def _advanced_metadata_rows(self, record: PatentRecord) -> list[dict[str, str]]:
        return [
            {"Field": "Analysis ID", "Value": record.analysis_id},
            {"Field": "Internal source label", "Value": record.source.value},
            {"Field": "Source URL", "Value": display_value(record.source_url)},
        ]

    def _other_analysis_id(self, analysis_id: str, signal: OverlapRiskSignal) -> str:
        if analysis_id == signal.source_analysis_id:
            return str(signal.target_analysis_id)
        return str(signal.source_analysis_id)


def _record_by_analysis_id(records: list[PatentRecord]) -> dict[str, PatentRecord]:
    return {record.analysis_id: record for record in records}


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
