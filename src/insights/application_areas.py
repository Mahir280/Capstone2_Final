"""Deterministic rule-based application-area suggestions for patent records."""

import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.models.patent import PatentRecord

TITLE_MATCH_WEIGHT = 3.0
KEYWORD_MATCH_WEIGHT = 3.0
ABSTRACT_MATCH_WEIGHT = 1.0
SCORE_MULTIPLIER = 10.0
DEFAULT_MIN_SCORE = 10.0
LIMITED_TEXT_TOKEN_THRESHOLD = 3
REPRESENTATIVE_TITLE_LIMIT = 3

_APPLICATION_AREA_RULES: dict[str, tuple[str, ...]] = {
    "Healthcare monitoring": (
        "health",
        "healthcare",
        "medical",
        "biosignal",
        "physiological",
        "heart rate",
        "ecg",
        "emg",
        "respiration",
        "sweat",
        "patient",
        "monitoring",
    ),
    "Sports and fitness wearables": (
        "sports",
        "fitness",
        "athlete",
        "exercise",
        "motion",
        "activity",
        "performance",
        "training",
        "wearable sensor",
    ),
    "Smart garments": (
        "garment",
        "clothing",
        "apparel",
        "shirt",
        "fabric",
        "textile",
        "smart textile",
        "e-textile",
        "wearable textile",
    ),
    "Textile electrodes": (
        "electrode",
        "conductive fiber",
        "conductive yarn",
        "textile electrode",
        "signal acquisition",
        "skin contact",
    ),
    "Rehabilitation": (
        "rehabilitation",
        "therapy",
        "recovery",
        "movement tracking",
        "gait",
        "posture",
        "assistive",
        "physiotherapy",
    ),
    "Safety and protective clothing": (
        "safety",
        "protective",
        "hazard",
        "worker",
        "industrial",
        "emergency",
        "firefighter",
        "protection",
        "alert",
    ),
    "Military and field monitoring": (
        "soldier",
        "military",
        "field",
        "tactical",
        "fatigue",
        "environment monitoring",
        "body status",
    ),
    "Energy harvesting textiles": (
        "energy harvesting",
        "triboelectric",
        "piezoelectric",
        "solar",
        "power generation",
        "self-powered",
        "battery-free",
    ),
    "Flexible sensors": (
        "flexible sensor",
        "strain sensor",
        "pressure sensor",
        "temperature sensor",
        "humidity sensor",
        "deformation",
        "stretchable",
        "flexible electronics",
    ),
    "Human-machine interaction textiles": (
        "human-machine interaction",
        "hmi",
        "gesture",
        "interface",
        "touch",
        "control",
        "interaction",
        "input device",
    ),
}


@dataclass(slots=True)
class ApplicationAreaSuggestion:
    """One explainable candidate application-area suggestion."""

    area_name: str
    score: float
    matched_terms: list[str]
    evidence_count: int
    explanation: str


@dataclass(slots=True)
class PatentApplicationAreaResult:
    """Application-area suggestions for one patent record."""

    analysis_id: str
    patent_id: str
    source: str
    title: str
    suggestions: list[ApplicationAreaSuggestion]
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ClusterApplicationAreaResult:
    """Application-area suggestions for one cluster of patent records."""

    cluster_id: int
    patent_count: int
    suggestions: list[ApplicationAreaSuggestion]
    evidence_terms: list[str]
    representative_titles: list[str]
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ApplicationAreaAnalysisResult:
    """Patent-level and cluster-level application-area analysis output."""

    patent_results: list[PatentApplicationAreaResult]
    cluster_results: list[ClusterApplicationAreaResult]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _TextFields:
    title: str
    abstract: str
    keywords: str


class ApplicationAreaSuggestionService:
    """Suggest candidate application areas using fixed keyword/rule evidence."""

    def __init__(self, min_score: float = DEFAULT_MIN_SCORE) -> None:
        self.min_score = _bounded_min_score(min_score)

    def suggest_for_patents(
        self,
        records: list[PatentRecord],
    ) -> list[PatentApplicationAreaResult]:
        """Return deterministic patent-level application-area suggestions."""
        results: list[PatentApplicationAreaResult] = []
        for record in records:
            warnings = self._record_warnings(record)
            suggestions = self._suggest_from_text_fields(
                _text_fields_for_record(record)
            )
            if not suggestions:
                warnings.append(
                    "No application-area evidence terms were detected from title, "
                    "abstract, or keywords."
                )

            results.append(
                PatentApplicationAreaResult(
                    analysis_id=record.analysis_id,
                    patent_id=record.patent_id,
                    source=record.source.value,
                    title=record.title,
                    suggestions=suggestions,
                    warnings=warnings,
                )
            )
        return results

    def suggest_for_clusters(
        self,
        records: list[PatentRecord],
        cluster_assignments: Mapping[str, int],
    ) -> list[ClusterApplicationAreaResult]:
        """Return deterministic cluster-level application-area suggestions."""
        cluster_results, _warnings = self._suggest_for_clusters_with_warnings(
            records,
            cluster_assignments,
        )
        return cluster_results

    def analyze(
        self,
        records: list[PatentRecord],
        cluster_assignments: Mapping[str, int] | None = None,
    ) -> ApplicationAreaAnalysisResult:
        """Return patent and optional cluster application-area suggestions."""
        warnings: list[str] = []
        if not records:
            warnings.append(
                "No patent records were provided for application-area analysis."
            )
            return ApplicationAreaAnalysisResult(
                patent_results=[],
                cluster_results=[],
                warnings=warnings,
            )

        patent_results = self.suggest_for_patents(records)
        limited_record_count = sum(
            1
            for result in patent_results
            if any("very limited" in warning for warning in result.warnings)
        )
        if limited_record_count:
            warnings.append(
                f"{limited_record_count} patent record(s) have very limited "
                "title/abstract/keyword text."
            )

        if not any(result.suggestions for result in patent_results):
            warnings.append(
                "No application-area evidence terms were detected in the provided "
                "patent records."
            )

        cluster_results: list[ClusterApplicationAreaResult] = []
        if cluster_assignments is not None:
            cluster_results, cluster_warnings = (
                self._suggest_for_clusters_with_warnings(
                    records,
                    cluster_assignments,
                )
            )
            warnings.extend(cluster_warnings)

        return ApplicationAreaAnalysisResult(
            patent_results=patent_results,
            cluster_results=cluster_results,
            warnings=warnings,
        )

    def _suggest_for_clusters_with_warnings(
        self,
        records: list[PatentRecord],
        cluster_assignments: Mapping[str, int],
    ) -> tuple[list[ClusterApplicationAreaResult], list[str]]:
        warnings: list[str] = []
        if not records:
            warnings.append(
                "No patent records were provided for cluster application-area analysis."
            )
            return [], warnings
        if not cluster_assignments:
            warnings.append(
                "No cluster assignments were provided for application-area analysis."
            )
            return [], warnings

        records_by_analysis_id = {record.analysis_id: record for record in records}
        records_by_cluster: dict[int, list[PatentRecord]] = defaultdict(list)
        missing_analysis_ids: list[str] = []
        for analysis_id, cluster_id in sorted(cluster_assignments.items()):
            record = records_by_analysis_id.get(analysis_id)
            if record is None:
                missing_analysis_ids.append(analysis_id)
                continue
            records_by_cluster[int(cluster_id)].append(record)

        if missing_analysis_ids:
            warnings.append(
                f"{len(missing_analysis_ids)} cluster assignment(s) referenced "
                "analysis identifiers that were not found in the patent records."
            )
        if not records_by_cluster:
            warnings.append(
                "No valid cluster assignments matched the provided patent records."
            )
            return [], warnings

        cluster_results: list[ClusterApplicationAreaResult] = []
        for cluster_id, cluster_records in sorted(records_by_cluster.items()):
            suggestions = self._suggest_from_text_fields(
                _text_fields_for_records(cluster_records)
            )
            result_warnings: list[str] = []
            if not suggestions:
                result_warnings.append(
                    "No application-area evidence terms were detected for this "
                    "cluster."
                )
            if all(_has_limited_text(record) for record in cluster_records):
                result_warnings.append(
                    "Cluster records have very limited title/abstract/keyword text."
                )

            cluster_results.append(
                ClusterApplicationAreaResult(
                    cluster_id=cluster_id,
                    patent_count=len(cluster_records),
                    suggestions=suggestions,
                    evidence_terms=_unique_terms_from_suggestions(suggestions),
                    representative_titles=[
                        record.title or record.patent_id
                        for record in cluster_records[:REPRESENTATIVE_TITLE_LIMIT]
                    ],
                    warnings=result_warnings,
                )
            )

        return cluster_results, warnings

    def _suggest_from_text_fields(
        self,
        text_fields: _TextFields,
    ) -> list[ApplicationAreaSuggestion]:
        suggestions: list[ApplicationAreaSuggestion] = []
        for area_name, terms in _APPLICATION_AREA_RULES.items():
            matched_terms: list[str] = []
            weighted_total = 0.0
            for term in terms:
                term_score = _term_score(term, text_fields)
                if term_score <= 0:
                    continue
                matched_terms.append(term)
                weighted_total += term_score

            score = round(min(100.0, weighted_total * SCORE_MULTIPLIER), 2)
            if score < self.min_score or not matched_terms:
                continue

            suggestions.append(
                ApplicationAreaSuggestion(
                    area_name=area_name,
                    score=score,
                    matched_terms=matched_terms,
                    evidence_count=len(matched_terms),
                    explanation=_explanation(area_name, matched_terms),
                )
            )

        return sorted(
            suggestions,
            key=lambda suggestion: (-suggestion.score, suggestion.area_name),
        )

    def _record_warnings(self, record: PatentRecord) -> list[str]:
        if _has_limited_text(record):
            return [
                "Patent text is very limited; application-area suggestions may be "
                "sparse."
            ]
        return []


def _term_score(term: str, text_fields: _TextFields) -> float:
    normalized_term = _normalize_text(term)
    if not normalized_term:
        return 0.0

    score = 0.0
    if _contains_term(text_fields.title, normalized_term):
        score += TITLE_MATCH_WEIGHT
    if _contains_term(text_fields.keywords, normalized_term):
        score += KEYWORD_MATCH_WEIGHT
    if _contains_term(text_fields.abstract, normalized_term):
        score += ABSTRACT_MATCH_WEIGHT
    return score


def _contains_term(text: str, normalized_term: str) -> bool:
    if not text:
        return False

    escaped_term = re.escape(normalized_term).replace(r"\ ", r"\s+")
    pattern = rf"(?<!\w){escaped_term}(?!\w)"
    return re.search(pattern, text) is not None


def _text_fields_for_record(record: PatentRecord) -> _TextFields:
    return _TextFields(
        title=_normalize_text(record.title),
        abstract=_normalize_text(record.abstract),
        keywords=_normalize_text(" ".join(record.keywords)),
    )


def _text_fields_for_records(records: list[PatentRecord]) -> _TextFields:
    return _TextFields(
        title=_normalize_text(" ".join(record.title for record in records)),
        abstract=_normalize_text(" ".join(record.abstract for record in records)),
        keywords=_normalize_text(
            " ".join(keyword for record in records for keyword in record.keywords)
        ),
    )


def _has_limited_text(record: PatentRecord) -> bool:
    text = " ".join([record.title, record.abstract, " ".join(record.keywords)])
    return len(_normalize_text(text).split()) < LIMITED_TEXT_TOKEN_THRESHOLD


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _unique_terms_from_suggestions(
    suggestions: list[ApplicationAreaSuggestion],
) -> list[str]:
    terms: list[str] = []
    seen_terms: set[str] = set()
    for suggestion in suggestions:
        for term in suggestion.matched_terms:
            if term in seen_terms:
                continue
            seen_terms.add(term)
            terms.append(term)
    return terms


def _explanation(area_name: str, matched_terms: list[str]) -> str:
    evidence_terms = ", ".join(matched_terms)
    return (
        f"Candidate application area '{area_name}' is suggested by deterministic "
        "keyword/rule evidence from title/abstract/keywords: "
        f"{evidence_terms}. The confidence score is an exploratory insight from "
        "matched evidence terms."
    )


def _bounded_min_score(min_score: float) -> float:
    return min(100.0, max(0.0, float(min_score)))
