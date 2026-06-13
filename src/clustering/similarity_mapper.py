"""TF-IDF similarity mapping for patent relationship validation."""

from dataclasses import dataclass, field

from sklearn.metrics.pairwise import cosine_similarity

from src.features.tfidf import TfidfFeatureResult
from src.models.patent import PatentRecord


@dataclass(slots=True)
class PatentSimilarityEdge:
    """A text-similarity relationship between two patent records."""

    source_analysis_id: str
    target_analysis_id: str
    similarity_score: float
    source_patent_id: str
    target_patent_id: str
    source_title: str
    target_title: str


@dataclass(slots=True)
class PatentSimilarityResult:
    """Structured result from a TF-IDF cosine-similarity mapping pass."""

    edges: list[PatentSimilarityEdge]
    patents_analyzed: int
    threshold: float
    top_k: int
    warnings: list[str] = field(default_factory=list)

    @property
    def edge_count(self) -> int:
        """Return the number of related patent pairs found."""
        return len(self.edges)


class TfidfSimilarityMapper:
    """Build simple patent relationship edges from TF-IDF cosine similarity."""

    def map_relationships(
        self,
        records: list[PatentRecord],
        tfidf_result: TfidfFeatureResult,
        *,
        similarity_threshold: float,
        top_k: int,
    ) -> PatentSimilarityResult:
        """Return undirected related-patent edges above the selected threshold."""
        warnings: list[str] = []
        threshold = self._bounded_threshold(similarity_threshold, warnings)

        if top_k < 1:
            warnings.append(
                "top_k must be at least 1 to produce similarity relationships."
            )
            return self._empty_result(0, threshold, top_k, warnings)

        if not tfidf_result.is_valid or tfidf_result.matrix is None:
            if tfidf_result.error:
                warnings.append(
                    f"TF-IDF features are not available: {tfidf_result.error}"
                )
            else:
                warnings.append(
                    "TF-IDF features are not available for similarity mapping."
                )
            return self._empty_result(0, threshold, top_k, warnings)

        matrix = tfidf_result.matrix
        sample_count = matrix.shape[0]
        if sample_count != len(tfidf_result.analysis_ids):
            warnings.append(
                "TF-IDF row count does not match the number of analysis identifiers."
            )
            return self._empty_result(0, threshold, top_k, warnings)

        if len(set(tfidf_result.analysis_ids)) != len(tfidf_result.analysis_ids):
            warnings.append(
                "TF-IDF analysis identifiers must be unique for similarity mapping."
            )
            return self._empty_result(sample_count, threshold, top_k, warnings)

        record_analysis_ids = [record.analysis_id for record in records]
        if len(set(record_analysis_ids)) != len(record_analysis_ids):
            warnings.append(
                "Patent records must have unique analysis identifiers for "
                "similarity mapping."
            )
            return self._empty_result(sample_count, threshold, top_k, warnings)

        records_by_id = {record.analysis_id: record for record in records}
        missing_ids = [
            analysis_id
            for analysis_id in tfidf_result.analysis_ids
            if analysis_id not in records_by_id
        ]
        if missing_ids:
            warnings.append(
                "TF-IDF analysis identifiers do not match the provided patent records."
            )
            return self._empty_result(sample_count, threshold, top_k, warnings)

        if sample_count < 2:
            warnings.append("At least 2 patents are required for similarity mapping.")
            return self._empty_result(sample_count, threshold, top_k, warnings)

        candidates = self._candidate_pairs(
            tfidf_result.analysis_ids,
            cosine_similarity(matrix),
            threshold,
        )
        edges = self._select_top_edges(candidates, records_by_id, top_k)

        if not edges:
            warnings.append(
                "No similarity relationships met the selected threshold and top_k."
            )

        return PatentSimilarityResult(
            edges=edges,
            patents_analyzed=sample_count,
            threshold=threshold,
            top_k=top_k,
            warnings=warnings,
        )

    def _candidate_pairs(
        self,
        analysis_ids: list[str],
        similarity_matrix: object,
        threshold: float,
    ) -> list[tuple[float, str, str]]:
        candidates: list[tuple[float, str, str]] = []
        for source_index, source_analysis_id in enumerate(analysis_ids):
            for target_index in range(source_index + 1, len(analysis_ids)):
                target_analysis_id = analysis_ids[target_index]
                score = self._bounded_score(
                    float(similarity_matrix[source_index, target_index])
                )
                if score <= 0 or score < threshold:
                    continue
                candidates.append((score, source_analysis_id, target_analysis_id))

        return sorted(candidates, key=lambda item: (-item[0], item[1], item[2]))

    def _select_top_edges(
        self,
        candidates: list[tuple[float, str, str]],
        records_by_id: dict[str, PatentRecord],
        top_k: int,
    ) -> list[PatentSimilarityEdge]:
        relationship_counts = {analysis_id: 0 for analysis_id in records_by_id}
        edges: list[PatentSimilarityEdge] = []

        for score, source_analysis_id, target_analysis_id in candidates:
            if relationship_counts[source_analysis_id] >= top_k:
                continue
            if relationship_counts[target_analysis_id] >= top_k:
                continue

            source_record = records_by_id[source_analysis_id]
            target_record = records_by_id[target_analysis_id]
            edges.append(
                PatentSimilarityEdge(
                    source_analysis_id=source_analysis_id,
                    target_analysis_id=target_analysis_id,
                    similarity_score=score,
                    source_patent_id=source_record.patent_id,
                    target_patent_id=target_record.patent_id,
                    source_title=source_record.title,
                    target_title=target_record.title,
                )
            )
            relationship_counts[source_analysis_id] += 1
            relationship_counts[target_analysis_id] += 1

        return edges

    def _bounded_threshold(
        self,
        similarity_threshold: float,
        warnings: list[str],
    ) -> float:
        if similarity_threshold < 0:
            warnings.append("Similarity threshold was below 0 and was adjusted to 0.")
            return 0.0
        if similarity_threshold > 1:
            warnings.append("Similarity threshold was above 1 and was adjusted to 1.")
            return 1.0
        return float(similarity_threshold)

    def _bounded_score(self, score: float) -> float:
        return min(1.0, max(0.0, score))

    def _empty_result(
        self,
        patents_analyzed: int,
        threshold: float,
        top_k: int,
        warnings: list[str],
    ) -> PatentSimilarityResult:
        return PatentSimilarityResult(
            edges=[],
            patents_analyzed=patents_analyzed,
            threshold=threshold,
            top_k=top_k,
            warnings=warnings,
        )
