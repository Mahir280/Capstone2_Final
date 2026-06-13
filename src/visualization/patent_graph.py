"""Graph-ready patent map structures built from similarity relationships."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

import networkx as nx

from src.clustering.similarity_mapper import PatentSimilarityResult
from src.models.patent import PatentRecord


@dataclass(slots=True)
class PatentGraphNode:
    """One patent node in the exploratory similarity graph."""

    analysis_id: str
    patent_id: str
    source: str
    title: str
    assignee: str | None
    country: str | None
    cluster_id: int | None
    degree: int
    x: float
    y: float


@dataclass(slots=True)
class PatentGraphEdge:
    """One undirected similarity edge between two patent nodes."""

    source_analysis_id: str
    target_analysis_id: str
    similarity_score: float
    relationship_strength: str


@dataclass(slots=True)
class PatentGraphResult:
    """Structured graph payload ready for dashboard rendering."""

    nodes: list[PatentGraphNode]
    edges: list[PatentGraphEdge]
    warnings: list[str] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        """Return the number of patent nodes in the graph."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Return the number of similarity edges in the graph."""
        return len(self.edges)

    @property
    def cluster_count(self) -> int:
        """Return the number of distinct non-empty cluster identifiers."""
        return len(
            {node.cluster_id for node in self.nodes if node.cluster_id is not None}
        )


class PatentGraphBuilder:
    """Convert saved patents and similarity edges into a stable graph layout."""

    def build(
        self,
        records: list[PatentRecord],
        similarity_result: PatentSimilarityResult,
        cluster_assignments: Mapping[str, int] | None = None,
        *,
        min_similarity: float = 0.25,
        max_edges: int | None = None,
        layout_seed: int = 42,
    ) -> PatentGraphResult:
        """Build a graph-ready result keyed by patent analysis identifiers."""
        warnings: list[str] = []
        if not records:
            return PatentGraphResult(
                nodes=[],
                edges=[],
                warnings=["No patent records are available for patent map generation."],
            )

        record_ids = [record.analysis_id for record in records]
        if len(set(record_ids)) != len(record_ids):
            return PatentGraphResult(
                nodes=[],
                edges=[],
                warnings=[
                    "Patent records must have unique analysis identifiers for "
                    "patent map generation."
                ],
            )

        bounded_similarity = self._bounded_similarity(min_similarity, warnings)
        bounded_max_edges = self._bounded_max_edges(max_edges, warnings)
        records_by_id = {record.analysis_id: record for record in records}
        graph_edges = self._graph_edges(
            similarity_result,
            records_by_id,
            min_similarity=bounded_similarity,
            max_edges=bounded_max_edges,
            warnings=warnings,
        )
        degree_by_id = {analysis_id: 0 for analysis_id in records_by_id}
        for edge in graph_edges:
            degree_by_id[edge.source_analysis_id] += 1
            degree_by_id[edge.target_analysis_id] += 1

        positions = self._positions(record_ids, graph_edges, layout_seed=layout_seed)
        nodes = [
            PatentGraphNode(
                analysis_id=record.analysis_id,
                patent_id=record.patent_id,
                source=record.source.value,
                title=record.title,
                assignee=record.assignee,
                country=record.country,
                cluster_id=(
                    None
                    if cluster_assignments is None
                    else cluster_assignments.get(record.analysis_id)
                ),
                degree=degree_by_id[record.analysis_id],
                x=positions[record.analysis_id][0],
                y=positions[record.analysis_id][1],
            )
            for record in records
        ]
        return PatentGraphResult(nodes=nodes, edges=graph_edges, warnings=warnings)

    def _graph_edges(
        self,
        similarity_result: PatentSimilarityResult,
        records_by_id: Mapping[str, PatentRecord],
        *,
        min_similarity: float,
        max_edges: int | None,
        warnings: list[str],
    ) -> list[PatentGraphEdge]:
        best_score_by_pair: dict[tuple[str, str], float] = {}
        skipped_missing_record = False

        for similarity_edge in similarity_result.edges:
            source_analysis_id = similarity_edge.source_analysis_id
            target_analysis_id = similarity_edge.target_analysis_id
            if source_analysis_id == target_analysis_id:
                continue

            if (
                source_analysis_id not in records_by_id
                or target_analysis_id not in records_by_id
            ):
                skipped_missing_record = True
                continue

            pair = tuple(sorted((source_analysis_id, target_analysis_id)))
            score = self._bounded_score(float(similarity_edge.similarity_score))
            if score < min_similarity:
                continue

            current_best_score = best_score_by_pair.get(pair)
            if current_best_score is None or score > current_best_score:
                best_score_by_pair[pair] = score

        edges = [
            PatentGraphEdge(
                source_analysis_id=pair[0],
                target_analysis_id=pair[1],
                similarity_score=score,
                relationship_strength=self._relationship_strength(score),
            )
            for pair, score in best_score_by_pair.items()
        ]
        if skipped_missing_record:
            warnings.append(
                "Some similarity relationships referenced patents outside the "
                "current dataset and were skipped."
            )

        ordered_edges = sorted(
            edges,
            key=lambda edge: (
                -edge.similarity_score,
                edge.source_analysis_id,
                edge.target_analysis_id,
            ),
        )
        if max_edges is not None:
            return ordered_edges[:max_edges]
        return ordered_edges

    def _positions(
        self,
        analysis_ids: list[str],
        edges: list[PatentGraphEdge],
        *,
        layout_seed: int,
    ) -> dict[str, tuple[float, float]]:
        if not edges:
            return self._fallback_positions(analysis_ids)

        graph = nx.Graph()
        graph.add_nodes_from(sorted(analysis_ids))
        for edge in edges:
            graph.add_edge(
                edge.source_analysis_id,
                edge.target_analysis_id,
                weight=edge.similarity_score,
            )

        layout = nx.spring_layout(graph, seed=layout_seed, weight="weight")
        return {
            analysis_id: (float(position[0]), float(position[1]))
            for analysis_id, position in layout.items()
        }

    def _fallback_positions(
        self,
        analysis_ids: list[str],
    ) -> dict[str, tuple[float, float]]:
        if len(analysis_ids) == 1:
            return {analysis_ids[0]: (0.0, 0.0)}

        ordered_ids = sorted(analysis_ids)
        positions: dict[str, tuple[float, float]] = {}
        total = len(ordered_ids)
        for index, analysis_id in enumerate(ordered_ids):
            angle = (2 * math.pi * index) / total
            positions[analysis_id] = (math.cos(angle), math.sin(angle))
        return positions

    def _bounded_similarity(self, min_similarity: float, warnings: list[str]) -> float:
        if min_similarity < 0:
            warnings.append("Minimum similarity was below 0 and was adjusted to 0.")
            return 0.0
        if min_similarity > 1:
            warnings.append("Minimum similarity was above 1 and was adjusted to 1.")
            return 1.0
        return float(min_similarity)

    def _bounded_max_edges(
        self,
        max_edges: int | None,
        warnings: list[str],
    ) -> int | None:
        if max_edges is None:
            return None
        if max_edges < 0:
            warnings.append("Maximum graph edges was below 0 and was adjusted to 0.")
            return 0
        return int(max_edges)

    def _bounded_score(self, score: float) -> float:
        return min(1.0, max(0.0, score))

    def _relationship_strength(self, similarity_score: float) -> str:
        if similarity_score >= 0.75:
            return "Strong"
        if similarity_score >= 0.50:
            return "Moderate"
        return "Weak"
