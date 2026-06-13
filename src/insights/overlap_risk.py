"""Explainable similarity-based overlap-risk indication for patent records."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.clustering.similarity_mapper import PatentSimilarityResult
from src.models.patent import PatentRecord


@dataclass(slots=True)
class OverlapRiskSignal:
    """One explainable similarity-based overlap signal between two patents."""

    source_analysis_id: str
    target_analysis_id: str
    source_patent_id: str
    target_patent_id: str
    source_title: str
    target_title: str
    similarity_score: float
    source_cluster_id: int | None
    target_cluster_id: int | None
    shared_cluster: bool
    shared_keywords: list[str]
    risk_score: float
    risk_level: str
    explanation: str


@dataclass(slots=True)
class OverlapRiskResult:
    """Ranked overlap-risk signals and non-fatal service warnings."""

    signals: list[OverlapRiskSignal]
    warnings: list[str] = field(default_factory=list)
    min_risk_score: float = 0.0

    @property
    def signal_count(self) -> int:
        """Return the number of overlap-risk signals."""
        return len(self.signals)

    @property
    def level_counts(self) -> dict[str, int]:
        """Return deterministic counts by risk level."""
        counts = Counter(signal.risk_level for signal in self.signals)
        return {
            "High": counts["High"],
            "Medium": counts["Medium"],
            "Low": counts["Low"],
            "Minimal": counts["Minimal"],
        }


class OverlapRiskService:
    """Score similarity edges using text, cluster, and keyword evidence."""

    def evaluate(
        self,
        records: list[PatentRecord],
        similarity_result: PatentSimilarityResult,
        cluster_assignments: Mapping[str, int] | None = None,
        *,
        min_risk_score: float = 0.0,
    ) -> OverlapRiskResult:
        """Return ranked explainable overlap-risk signals."""
        warnings = list(similarity_result.warnings)
        bounded_min_risk_score = self._bounded_min_risk_score(min_risk_score, warnings)

        if not similarity_result.edges:
            warnings.append("No similarity relationships are available for scoring.")
            return OverlapRiskResult(
                signals=[],
                warnings=warnings,
                min_risk_score=bounded_min_risk_score,
            )

        records_by_id = self._records_by_analysis_id(records, warnings)
        if not records_by_id:
            return OverlapRiskResult(
                signals=[],
                warnings=warnings,
                min_risk_score=bounded_min_risk_score,
            )

        signals: list[OverlapRiskSignal] = []
        for edge in similarity_result.edges:
            source_record = records_by_id.get(edge.source_analysis_id)
            target_record = records_by_id.get(edge.target_analysis_id)
            if source_record is None or target_record is None:
                warnings.append(
                    "A similarity relationship was skipped because its analysis "
                    "identifier was not found in the patent records."
                )
                continue

            shared_keywords = self._shared_keywords(source_record, target_record)
            source_cluster_id = self._cluster_id(
                cluster_assignments, edge.source_analysis_id
            )
            target_cluster_id = self._cluster_id(
                cluster_assignments, edge.target_analysis_id
            )
            shared_cluster = (
                source_cluster_id is not None
                and target_cluster_id is not None
                and source_cluster_id == target_cluster_id
            )
            similarity_score = self._bounded_similarity(edge.similarity_score)
            risk_score = self._risk_score(
                similarity_score=similarity_score,
                shared_cluster=shared_cluster,
                shared_keyword_count=len(shared_keywords),
                source_keyword_count=len(self._keyword_set(source_record.keywords)),
                target_keyword_count=len(self._keyword_set(target_record.keywords)),
            )

            if risk_score < bounded_min_risk_score:
                continue

            signals.append(
                OverlapRiskSignal(
                    source_analysis_id=edge.source_analysis_id,
                    target_analysis_id=edge.target_analysis_id,
                    source_patent_id=edge.source_patent_id,
                    target_patent_id=edge.target_patent_id,
                    source_title=edge.source_title,
                    target_title=edge.target_title,
                    similarity_score=similarity_score,
                    source_cluster_id=source_cluster_id,
                    target_cluster_id=target_cluster_id,
                    shared_cluster=shared_cluster,
                    shared_keywords=shared_keywords,
                    risk_score=risk_score,
                    risk_level=self._risk_level(risk_score),
                    explanation=self._explanation(
                        similarity_score=similarity_score,
                        shared_cluster=shared_cluster,
                        has_cluster_context=(
                            source_cluster_id is not None
                            and target_cluster_id is not None
                        ),
                        shared_keywords=shared_keywords,
                    ),
                )
            )

        ranked_signals = sorted(
            signals,
            key=lambda signal: (
                -signal.risk_score,
                signal.source_analysis_id,
                signal.target_analysis_id,
            ),
        )
        return OverlapRiskResult(
            signals=ranked_signals,
            warnings=warnings,
            min_risk_score=bounded_min_risk_score,
        )

    def _records_by_analysis_id(
        self,
        records: list[PatentRecord],
        warnings: list[str],
    ) -> dict[str, PatentRecord]:
        analysis_ids = [record.analysis_id for record in records]
        if len(set(analysis_ids)) != len(analysis_ids):
            warnings.append(
                "Patent records must have unique analysis identifiers for "
                "overlap-risk indication."
            )
            return {}
        return {record.analysis_id: record for record in records}

    def _risk_score(
        self,
        *,
        similarity_score: float,
        shared_cluster: bool,
        shared_keyword_count: int,
        source_keyword_count: int,
        target_keyword_count: int,
    ) -> float:
        similarity_component = similarity_score * 70.0
        cluster_component = 15.0 if shared_cluster else 0.0
        keyword_component = self._keyword_component(
            shared_keyword_count,
            source_keyword_count,
            target_keyword_count,
        )
        return round(
            min(100.0, similarity_component + cluster_component + keyword_component),
            4,
        )

    def _keyword_component(
        self,
        shared_keyword_count: int,
        source_keyword_count: int,
        target_keyword_count: int,
    ) -> float:
        max_keyword_count = max(source_keyword_count, target_keyword_count)
        if shared_keyword_count <= 0 or max_keyword_count <= 0:
            return 0.0
        return min(15.0, (shared_keyword_count / max_keyword_count) * 15.0)

    def _risk_level(self, risk_score: float) -> str:
        if risk_score >= 75:
            return "High"
        if risk_score >= 50:
            return "Medium"
        if risk_score >= 25:
            return "Low"
        return "Minimal"

    def _explanation(
        self,
        *,
        similarity_score: float,
        shared_cluster: bool,
        has_cluster_context: bool,
        shared_keywords: list[str],
    ) -> str:
        parts = [f"TF-IDF similarity is {similarity_score:.2f}"]
        if shared_cluster:
            parts.append("patents are in the same cluster")
        elif has_cluster_context:
            parts.append("patents are in different clusters")

        if shared_keywords:
            parts.append(f"shared keywords: {', '.join(shared_keywords)}")
        else:
            parts.append("no shared keywords were found")

        return f"{'; '.join(parts)}."

    def _shared_keywords(
        self,
        source_record: PatentRecord,
        target_record: PatentRecord,
    ) -> list[str]:
        return sorted(
            self._keyword_set(source_record.keywords)
            & self._keyword_set(target_record.keywords)
        )

    def _keyword_set(self, keywords: list[str]) -> set[str]:
        return {
            cleaned_keyword
            for cleaned_keyword in (_clean_keyword(keyword) for keyword in keywords)
            if cleaned_keyword
        }

    def _cluster_id(
        self,
        cluster_assignments: Mapping[str, int] | None,
        analysis_id: str,
    ) -> int | None:
        if not cluster_assignments or analysis_id not in cluster_assignments:
            return None
        return int(cluster_assignments[analysis_id])

    def _bounded_similarity(self, similarity_score: float) -> float:
        return min(1.0, max(0.0, float(similarity_score)))

    def _bounded_min_risk_score(
        self,
        min_risk_score: float,
        warnings: list[str],
    ) -> float:
        if min_risk_score < 0:
            warnings.append("Minimum risk score was below 0 and was adjusted to 0.")
            return 0.0
        if min_risk_score > 100:
            warnings.append("Minimum risk score was above 100 and was adjusted to 100.")
            return 100.0
        return float(min_risk_score)


def _clean_keyword(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())
