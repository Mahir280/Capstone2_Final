"""Application service for JSON-ready patent landscape assembly."""

import re
from typing import Any

from src.application._formatting import (
    evidence_level_label,
    format_patent_authority,
    grouping_quality_label,
    primary_authority_label,
    record_year,
    relationship_strength_label,
    shorten,
    technology_group_label,
)
from src.application.dto import LandscapeDTO, LandscapeEdgeDTO, LandscapeNodeDTO
from src.clustering.kmeans_clusterer import KMeansPatentClusterer
from src.clustering.similarity_mapper import PatentSimilarityEdge, TfidfSimilarityMapper
from src.features.tfidf import TfidfFeatureResult, TfidfFeatureService
from src.insights import ApplicationAreaSuggestionService
from src.models.patent import PatentRecord
from src.visualization import PatentGraphBuilder


class LandscapeService:
    """Build API-ready landscape graph DTOs from reusable core modules."""

    def __init__(
        self,
        *,
        tfidf_service: TfidfFeatureService | None = None,
        clusterer: KMeansPatentClusterer | None = None,
        similarity_mapper: TfidfSimilarityMapper | None = None,
        application_service: ApplicationAreaSuggestionService | None = None,
        graph_builder: PatentGraphBuilder | None = None,
    ) -> None:
        self.tfidf_service = tfidf_service or TfidfFeatureService()
        self.clusterer = clusterer or KMeansPatentClusterer()
        self.similarity_mapper = similarity_mapper or TfidfSimilarityMapper()
        self.application_service = (
            application_service or ApplicationAreaSuggestionService()
        )
        self.graph_builder = graph_builder or PatentGraphBuilder()

    def build_landscape(
        self,
        records: list[PatentRecord],
        *,
        tfidf_result: TfidfFeatureResult | None = None,
        selected_analysis_id: str | None = None,
        focused: bool = False,
        relationship_threshold: float = 0.20,
        top_k: int = 5,
        technology_group_count: int = 7,
        max_edges: int | None = 80,
        min_application_score: float = 0.0,
    ) -> LandscapeDTO:
        """Return a serializable patent landscape graph and group summaries."""
        settings: dict[str, int | float | str | bool | None] = {
            "relationship_threshold": relationship_threshold,
            "top_k": top_k,
            "technology_group_count": technology_group_count,
            "max_edges": max_edges,
            "focused": focused,
        }
        if not records:
            return self._empty_landscape(
                selected_analysis_id,
                settings,
                ["No patent records are available for landscape generation."],
            )

        features = tfidf_result or self.tfidf_service.build_from_patents(records)
        if not features.is_valid:
            message = features.error or "Keyword evidence is not available."
            return self._empty_landscape(selected_analysis_id, settings, [message])

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
        application_result = self.application_service.analyze(
            records,
            cluster_result.assignments,
        )
        candidate_areas = self._candidate_areas_by_analysis_id(application_result)
        records_for_graph = records
        if focused and selected_analysis_id is not None:
            records_for_graph = self._focused_records(
                records,
                selected_analysis_id,
                similarity_result.edges,
            )

        graph_result = self.graph_builder.build(
            records_for_graph,
            similarity_result,
            cluster_result.assignments,
            min_similarity=relationship_threshold,
            max_edges=max_edges,
        )
        nodes = [
            LandscapeNodeDTO(
                analysis_id=node.analysis_id,
                patent_id=node.patent_id,
                source=node.source,
                source_authority=format_patent_authority(node),
                title=node.title,
                assignee=node.assignee,
                country=node.country,
                technology_group_id=node.cluster_id,
                technology_group=technology_group_label(node.cluster_id),
                degree=node.degree,
                x=node.x,
                y=node.y,
                candidate_application_areas=candidate_areas.get(node.analysis_id, []),
                selected=node.analysis_id == selected_analysis_id,
            )
            for node in graph_result.nodes
        ]
        edges = [
            LandscapeEdgeDTO(
                source_analysis_id=edge.source_analysis_id,
                target_analysis_id=edge.target_analysis_id,
                relationship_strength=relationship_strength_label(
                    edge.similarity_score
                ),
                similarity_score=round(edge.similarity_score, 4),
            )
            for edge in graph_result.edges
        ]
        warnings = _dedupe(
            [
                *cluster_result.warnings,
                *similarity_result.warnings,
                *application_result.warnings,
                *graph_result.warnings,
            ]
        )
        node_count = len(nodes)
        edge_count = len(edges)
        return LandscapeDTO(
            nodes=nodes,
            edges=edges,
            node_count=node_count,
            edge_count=edge_count,
            technology_group_count=len(
                {
                    node.technology_group_id
                    for node in nodes
                    if node.technology_group_id is not None
                }
            ),
            average_relationships=(
                round(sum(node.degree for node in nodes) / float(node_count), 4)
                if node_count
                else 0.0
            ),
            selected_analysis_id=selected_analysis_id,
            settings=settings,
            technology_groups=self._technology_groups(
                cluster_result,
                application_result,
                min_application_score,
            ),
            technology_group_assignments=dict(cluster_result.assignments),
            grouping_quality_score=cluster_result.silhouette_score,
            warnings=warnings,
        )

    def _technology_groups(
        self,
        cluster_result: object,
        application_result: object,
        min_application_score: float,
    ) -> list[dict[str, Any]]:
        application_by_cluster = {
            result.cluster_id: result for result in application_result.cluster_results
        }
        summaries = list(cluster_result.summaries)
        group_names = self._distinct_group_names(summaries, application_by_cluster)
        groups: list[dict[str, Any]] = []
        for summary in summaries:
            application_row = application_by_cluster.get(summary.cluster_id)
            application_areas = self._group_application_areas(
                application_row,
                min_application_score,
            )
            groups.append(
                {
                    "technology_group_id": summary.cluster_id,
                    "technology_group": technology_group_label(summary.cluster_id),
                    "group_label": group_names[summary.cluster_id],
                    "patent_count": summary.size,
                    "grouping_quality": grouping_quality_label(
                        cluster_result.silhouette_score
                    ),
                    "grouping_quality_score": cluster_result.silhouette_score,
                    "top_terms": list(summary.top_terms),
                    "representative_titles": list(summary.representative_titles),
                    "candidate_application_areas": application_areas,
                }
            )
        return groups

    def _group_application_areas(
        self,
        application_row: object | None,
        min_application_score: float,
    ) -> list[dict[str, Any]]:
        if application_row is None:
            return []
        return [
            {
                "area_name": suggestion.area_name,
                "score": round(suggestion.score, 2),
                "evidence_level": evidence_level_label(suggestion.score),
                "matched_terms": list(suggestion.matched_terms),
                "label": (
                    f"{suggestion.area_name} - "
                    f"{evidence_level_label(suggestion.score)}"
                ),
            }
            for suggestion in application_row.suggestions
            if suggestion.score >= min_application_score
        ]

    def _group_name(self, summary: object, application_row: object | None) -> str:
        if application_row is not None and application_row.suggestions:
            return str(application_row.suggestions[0].area_name)
        if summary.top_terms:
            return ", ".join(summary.top_terms[:3])
        return "General patent group"

    def _distinct_group_names(
        self,
        summaries: list[Any],
        application_by_cluster: dict[int, Any],
    ) -> dict[int, str]:
        """Name every group, qualifying collisions with distinguishing evidence.

        The same application area can dominate several clusters in a narrow
        corpus, which previously produced identical labels for every group.
        Colliding groups keep their honest base name but gain a short qualifier
        drawn from their own top terms (terms the other colliding groups do not
        share), so legends and cards stay distinguishable without invented
        names.
        """
        base_names = {
            summary.cluster_id: self._group_name(
                summary, application_by_cluster.get(summary.cluster_id)
            )
            for summary in summaries
        }
        colliding_by_name: dict[str, list[Any]] = {}
        for summary in summaries:
            colliding_by_name.setdefault(base_names[summary.cluster_id], []).append(
                summary
            )
        names = dict(base_names)
        for base_name, colliding in colliding_by_name.items():
            if len(colliding) < 2:
                continue
            for summary in colliding:
                qualifier = self._group_qualifier(summary, colliding, base_name)
                if qualifier:
                    names[summary.cluster_id] = f"{base_name} — {qualifier} focus"
                else:
                    names[summary.cluster_id] = (
                        f"{base_name} — "
                        f"{technology_group_label(summary.cluster_id).lower()}"
                    )
        return names

    def _group_qualifier(
        self,
        summary: Any,
        colliding: list[Any],
        base_name: str,
    ) -> str | None:
        """Return up to two top terms unique to this group among the collisions.

        Terms that only restate the base name ("Flexible sensors — sensor")
        or repeat an already-picked term in another inflection ("sensor
        sensors") are skipped via a light suffix-stripping comparison.
        """
        other_terms = {
            term
            for other in colliding
            if other.cluster_id != summary.cluster_id
            for term in other.top_terms
        }
        used_stems: set[str] = set()
        for token in re.findall(r"[a-z0-9]+", base_name.casefold()):
            used_stems |= _stem_candidates(token)
        picked: list[str] = []
        for term in summary.top_terms:
            if term in other_terms:
                continue
            candidates = _stem_candidates(term.casefold())
            if candidates & used_stems:
                continue
            picked.append(term)
            used_stems |= candidates
            if len(picked) == 2:
                break
        if not picked:
            return None
        return " ".join(picked)

    def _candidate_areas_by_analysis_id(
        self,
        application_result: object,
    ) -> dict[str, list[str]]:
        return {
            result.analysis_id: [
                suggestion.area_name for suggestion in result.suggestions[:3]
            ]
            for result in application_result.patent_results
            if result.suggestions
        }

    def _focused_records(
        self,
        records: list[PatentRecord],
        selected_analysis_id: str,
        edges: list[PatentSimilarityEdge],
    ) -> list[PatentRecord]:
        selected_record = _record_by_analysis_id(records).get(selected_analysis_id)
        if selected_record is None:
            return records
        related_ids = {
            self._other_analysis_id(selected_analysis_id, edge)
            for edge in edges
            if selected_analysis_id
            in {edge.source_analysis_id, edge.target_analysis_id}
        }
        focused_ids = {selected_analysis_id, *related_ids}
        ordered_records = [
            record for record in records if record.analysis_id in focused_ids
        ]
        if selected_record not in ordered_records:
            ordered_records.insert(0, selected_record)
        return ordered_records

    def _other_analysis_id(
        self,
        analysis_id: str,
        edge: PatentSimilarityEdge,
    ) -> str:
        if analysis_id == edge.source_analysis_id:
            return str(edge.target_analysis_id)
        return str(edge.source_analysis_id)

    def _empty_landscape(
        self,
        selected_analysis_id: str | None,
        settings: dict[str, int | float | str | bool | None],
        warnings: list[str],
    ) -> LandscapeDTO:
        return LandscapeDTO(
            nodes=[],
            edges=[],
            node_count=0,
            edge_count=0,
            technology_group_count=0,
            average_relationships=0.0,
            selected_analysis_id=selected_analysis_id,
            settings=settings,
            warnings=warnings,
        )

    def group_patent_rows(
        self,
        records: list[PatentRecord],
        landscape: LandscapeDTO,
        technology_group_id: int,
    ) -> list[dict[str, str]]:
        """Return serializable patent rows for a selected technology group."""
        assignments = landscape.technology_group_assignments
        selected_records = [
            record
            for record in records
            if assignments.get(record.analysis_id) == technology_group_id
        ]
        return [
            {
                "Analysis ID": record.analysis_id,
                "Patent ID": record.patent_id,
                "Title": record.title,
                "Assignee": record.assignee or "",
                "Country": record.country or "",
                "Year": record_year(record) or "",
                "Source authority": primary_authority_label(record),
                "Important keywords": "; ".join(record.keywords),
                "Abstract preview": shorten(record.abstract),
            }
            for record in selected_records
        ]


def _stem_candidates(token: str) -> set[str]:
    """Return the token plus suffix-stripped variants for duplicate checks.

    Two tokens count as the same word when their candidate sets intersect,
    which catches pairs like "electrode"/"electrodes" and "heating"/"heated"
    without a full stemmer.
    """
    candidates = {token}
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            candidates.add(token[: -len(suffix)])
    return candidates


def _record_by_analysis_id(records: list[PatentRecord]) -> dict[str, PatentRecord]:
    return {record.analysis_id: record for record in records}


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
