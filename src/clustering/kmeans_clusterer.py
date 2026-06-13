"""Baseline KMeans clustering for TF-IDF patent features."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from src.features.tfidf import TfidfFeatureResult
from src.models.patent import PatentRecord


@dataclass(slots=True)
class ClusterSummary:
    """Human-readable summary for one baseline cluster."""

    cluster_id: int
    size: int
    top_terms: list[str]
    representative_titles: list[str] = field(default_factory=list)


@dataclass(slots=True)
class KMeansClusteringResult:
    """Structured result from the baseline KMeans clustering pass."""

    assignments: dict[str, int]
    requested_cluster_count: int
    selected_cluster_count: int
    actual_cluster_count: int
    silhouette_score: float | None
    cluster_sizes: dict[int, int]
    top_terms_by_cluster: dict[int, list[str]]
    summaries: list[ClusterSummary]
    warnings: list[str] = field(default_factory=list)


class KMeansPatentClusterer:
    """Run a simple deterministic KMeans baseline over TF-IDF patent rows."""

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state

    def cluster(
        self,
        records: list[PatentRecord],
        tfidf_result: TfidfFeatureResult,
        requested_cluster_count: int,
        *,
        top_terms_per_cluster: int = 8,
        representative_limit: int = 3,
    ) -> KMeansClusteringResult:
        """Cluster TF-IDF rows and return assignments keyed by analysis id."""
        warnings: list[str] = []
        empty_result = self._empty_result(requested_cluster_count, warnings)

        if not tfidf_result.is_valid or tfidf_result.matrix is None:
            if tfidf_result.error:
                warnings.append(
                    f"TF-IDF features are not available: {tfidf_result.error}"
                )
            else:
                warnings.append("TF-IDF features are not available for clustering.")
            return empty_result

        matrix = tfidf_result.matrix
        sample_count = matrix.shape[0]
        if sample_count != len(tfidf_result.analysis_ids):
            warnings.append(
                "TF-IDF row count does not match the number of analysis identifiers."
            )
            return empty_result

        if len(set(tfidf_result.analysis_ids)) != len(tfidf_result.analysis_ids):
            warnings.append(
                "TF-IDF analysis identifiers must be unique for clustering."
            )
            return empty_result

        record_ids = {record.analysis_id for record in records}
        missing_ids = [
            analysis_id
            for analysis_id in tfidf_result.analysis_ids
            if analysis_id not in record_ids
        ]
        if missing_ids:
            warnings.append(
                "TF-IDF analysis identifiers do not match the provided patent records."
            )
            return empty_result

        if sample_count < 2:
            warnings.append("At least 2 patents are required for KMeans clustering.")
            return empty_result

        selected_cluster_count = self._bound_cluster_count(
            requested_cluster_count, sample_count, warnings
        )
        model = KMeans(
            n_clusters=selected_cluster_count,
            random_state=self.random_state,
            n_init=10,
        )
        labels = model.fit_predict(matrix)
        assignments = {
            analysis_id: int(label)
            for analysis_id, label in zip(
                tfidf_result.analysis_ids, labels, strict=True
            )
        }
        cluster_sizes = dict(sorted(Counter(assignments.values()).items()))
        actual_cluster_count = len(cluster_sizes)

        if actual_cluster_count < selected_cluster_count:
            warnings.append(
                "KMeans produced fewer distinct clusters than requested; "
                "some input rows may be very similar."
            )

        top_terms_by_cluster = self._top_terms_by_cluster(
            model.cluster_centers_,
            tfidf_result.feature_names,
            cluster_sizes,
            top_terms_per_cluster,
        )
        summaries = self._summaries(
            records,
            tfidf_result.analysis_ids,
            assignments,
            cluster_sizes,
            top_terms_by_cluster,
            representative_limit,
        )
        score = self._silhouette_score(matrix, list(assignments.values()), warnings)

        return KMeansClusteringResult(
            assignments=assignments,
            requested_cluster_count=requested_cluster_count,
            selected_cluster_count=selected_cluster_count,
            actual_cluster_count=actual_cluster_count,
            silhouette_score=score,
            cluster_sizes=cluster_sizes,
            top_terms_by_cluster=top_terms_by_cluster,
            summaries=summaries,
            warnings=warnings,
        )

    def _bound_cluster_count(
        self,
        requested_cluster_count: int,
        sample_count: int,
        warnings: list[str],
    ) -> int:
        selected_cluster_count = requested_cluster_count
        if selected_cluster_count < 1:
            selected_cluster_count = 1
            warnings.append(
                "Requested cluster count was below 1 and was adjusted to 1."
            )

        max_supported_clusters = sample_count - 1
        if selected_cluster_count > max_supported_clusters:
            selected_cluster_count = max_supported_clusters
            warnings.append(
                "Requested cluster count was adjusted below the patent count "
                "so clustering and validation remain well-defined."
            )
        return selected_cluster_count

    def _silhouette_score(
        self,
        matrix: object,
        labels: list[int],
        warnings: list[str],
    ) -> float | None:
        sample_count = len(labels)
        label_count = len(set(labels))
        if label_count < 2:
            warnings.append(
                "Silhouette score is unavailable because fewer than 2 clusters exist."
            )
            return None
        if label_count >= sample_count:
            warnings.append(
                "Silhouette score is unavailable because each patent would be its own "
                "cluster."
            )
            return None

        try:
            return float(silhouette_score(matrix, labels))
        except ValueError as exc:
            warnings.append(f"Silhouette score is unavailable: {exc}")
            return None

    def _top_terms_by_cluster(
        self,
        cluster_centers: object,
        feature_names: list[str],
        cluster_sizes: dict[int, int],
        top_terms_per_cluster: int,
    ) -> dict[int, list[str]]:
        top_terms_by_cluster: dict[int, list[str]] = {}
        if top_terms_per_cluster <= 0:
            return {cluster_id: [] for cluster_id in cluster_sizes}

        for cluster_id in cluster_sizes:
            center = cluster_centers[cluster_id]
            scored_terms = [
                (feature_names[index], float(score))
                for index, score in enumerate(center)
                if score > 0
            ]
            top_terms_by_cluster[cluster_id] = [
                term
                for term, _score in sorted(
                    scored_terms, key=lambda item: (-item[1], item[0])
                )[:top_terms_per_cluster]
            ]
        return top_terms_by_cluster

    def _summaries(
        self,
        records: list[PatentRecord],
        analysis_ids: list[str],
        assignments: dict[str, int],
        cluster_sizes: dict[int, int],
        top_terms_by_cluster: dict[int, list[str]],
        representative_limit: int,
    ) -> list[ClusterSummary]:
        records_by_id = {record.analysis_id: record for record in records}
        titles_by_cluster: dict[int, list[str]] = defaultdict(list)
        for analysis_id in analysis_ids:
            cluster_id = assignments[analysis_id]
            record = records_by_id[analysis_id]
            title = record.title or record.patent_id
            if len(titles_by_cluster[cluster_id]) < representative_limit:
                titles_by_cluster[cluster_id].append(title)

        return [
            ClusterSummary(
                cluster_id=cluster_id,
                size=size,
                top_terms=top_terms_by_cluster.get(cluster_id, []),
                representative_titles=titles_by_cluster.get(cluster_id, []),
            )
            for cluster_id, size in sorted(cluster_sizes.items())
        ]

    def _empty_result(
        self,
        requested_cluster_count: int,
        warnings: list[str],
    ) -> KMeansClusteringResult:
        return KMeansClusteringResult(
            assignments={},
            requested_cluster_count=requested_cluster_count,
            selected_cluster_count=0,
            actual_cluster_count=0,
            silhouette_score=None,
            cluster_sizes={},
            top_terms_by_cluster={},
            summaries=[],
            warnings=warnings,
        )
