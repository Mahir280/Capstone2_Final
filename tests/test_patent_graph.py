"""Tests for the patent similarity graph builder."""

from src.clustering.similarity_mapper import (
    PatentSimilarityEdge,
    PatentSimilarityResult,
)
from src.models.enums import SourceType
from src.models.patent import PatentRecord
from src.visualization import PatentGraphBuilder


def test_empty_record_list_returns_safe_empty_graph_with_warning() -> None:
    result = PatentGraphBuilder().build([], _similarity_result([]))

    assert result.nodes == []
    assert result.edges == []
    assert result.node_count == 0
    assert result.edge_count == 0
    assert result.cluster_count == 0
    assert result.warnings == [
        "No patent records are available for patent map generation."
    ]


def test_one_node_is_created_per_patent_record() -> None:
    records = _sample_records()

    result = PatentGraphBuilder().build(records, _similarity_result([]))

    assert len(result.nodes) == len(records)
    assert {node.analysis_id for node in result.nodes} == {
        record.analysis_id for record in records
    }


def test_node_identity_uses_analysis_id_not_patent_id_alone() -> None:
    records = _duplicate_patent_id_records()

    result = PatentGraphBuilder().build(records, _similarity_result([]))

    assert {node.analysis_id for node in result.nodes} == {
        "CSV_IMPORT:DUPLICATE-1",
        "JSON_IMPORT:DUPLICATE-1",
        "CSV_IMPORT:US-UNIQUE-1",
    }
    assert {node.patent_id for node in result.nodes} == {"DUPLICATE-1", "US-UNIQUE-1"}


def test_duplicate_patent_ids_from_different_sources_do_not_collapse() -> None:
    records = _duplicate_patent_id_records()

    result = PatentGraphBuilder().build(records, _similarity_result([]))

    duplicate_nodes = [node for node in result.nodes if node.patent_id == "DUPLICATE-1"]
    assert len(duplicate_nodes) == 2
    assert {node.source for node in duplicate_nodes} == {"CSV_IMPORT", "JSON_IMPORT"}


def test_edges_are_created_from_similarity_relationships() -> None:
    records = _sample_records()
    similarity_result = _similarity_result(
        [
            ("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-2", 0.81),
            ("CSV_IMPORT:US-FIBER-2", "JSON_IMPORT:US-BATTERY-1", 0.54),
        ]
    )

    result = PatentGraphBuilder().build(records, similarity_result, min_similarity=0.25)

    assert result.edge_count == 2
    assert {
        (edge.source_analysis_id, edge.target_analysis_id) for edge in result.edges
    } == {
        ("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-2"),
        ("CSV_IMPORT:US-FIBER-2", "JSON_IMPORT:US-BATTERY-1"),
    }


def test_min_similarity_filters_weak_edges() -> None:
    records = _sample_records()
    similarity_result = _similarity_result(
        [
            ("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-2", 0.30),
            ("CSV_IMPORT:US-FIBER-2", "JSON_IMPORT:US-BATTERY-1", 0.61),
        ]
    )

    result = PatentGraphBuilder().build(records, similarity_result, min_similarity=0.50)

    assert result.edge_count == 1
    assert result.edges[0].similarity_score == 0.61


def test_max_edges_keeps_only_top_scoring_edges() -> None:
    records = _sample_records()
    similarity_result = _similarity_result(
        [
            ("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-2", 0.91),
            ("CSV_IMPORT:US-FIBER-1", "JSON_IMPORT:US-BATTERY-1", 0.72),
            ("CSV_IMPORT:US-FIBER-2", "JSON_IMPORT:US-BATTERY-1", 0.63),
        ]
    )

    result = PatentGraphBuilder().build(
        records,
        similarity_result,
        min_similarity=0.25,
        max_edges=2,
    )

    assert [edge.similarity_score for edge in result.edges] == [0.91, 0.72]


def test_node_degree_is_calculated_correctly() -> None:
    records = _sample_records()
    similarity_result = _similarity_result(
        [
            ("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-2", 0.84),
            ("CSV_IMPORT:US-FIBER-2", "JSON_IMPORT:US-BATTERY-1", 0.66),
        ]
    )

    result = PatentGraphBuilder().build(records, similarity_result, min_similarity=0.25)
    degree_by_analysis_id = {node.analysis_id: node.degree for node in result.nodes}

    assert degree_by_analysis_id == {
        "CSV_IMPORT:US-FIBER-1": 1,
        "CSV_IMPORT:US-FIBER-2": 2,
        "JSON_IMPORT:US-BATTERY-1": 1,
    }


def test_cluster_assignments_are_attached_using_analysis_id() -> None:
    records = _duplicate_patent_id_records()

    result = PatentGraphBuilder().build(
        records,
        _similarity_result([]),
        cluster_assignments={
            "CSV_IMPORT:DUPLICATE-1": 1,
            "JSON_IMPORT:DUPLICATE-1": 2,
        },
    )
    cluster_by_analysis_id = {
        node.analysis_id: node.cluster_id for node in result.nodes
    }

    assert cluster_by_analysis_id == {
        "CSV_IMPORT:DUPLICATE-1": 1,
        "JSON_IMPORT:DUPLICATE-1": 2,
        "CSV_IMPORT:US-UNIQUE-1": None,
    }
    assert result.cluster_count == 2


def test_relationship_strength_is_assigned_deterministically() -> None:
    records = _sample_records()
    similarity_result = _similarity_result(
        [
            ("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-2", 0.80),
            ("CSV_IMPORT:US-FIBER-1", "JSON_IMPORT:US-BATTERY-1", 0.50),
            ("CSV_IMPORT:US-FIBER-2", "JSON_IMPORT:US-BATTERY-1", 0.49),
        ]
    )

    result = PatentGraphBuilder().build(records, similarity_result, min_similarity=0.25)

    assert [
        (edge.similarity_score, edge.relationship_strength) for edge in result.edges
    ] == [
        (0.8, "Strong"),
        (0.5, "Moderate"),
        (0.49, "Weak"),
    ]


def test_graph_layout_positions_are_deterministic_with_fixed_seed() -> None:
    records = _sample_records()
    similarity_result = _similarity_result(
        [
            ("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-2", 0.82),
            ("CSV_IMPORT:US-FIBER-2", "JSON_IMPORT:US-BATTERY-1", 0.64),
        ]
    )

    first_result = PatentGraphBuilder().build(
        records, similarity_result, min_similarity=0.25, layout_seed=17
    )
    second_result = PatentGraphBuilder().build(
        records, similarity_result, min_similarity=0.25, layout_seed=17
    )

    first_positions = {
        node.analysis_id: (round(node.x, 8), round(node.y, 8))
        for node in first_result.nodes
    }
    second_positions = {
        node.analysis_id: (round(node.x, 8), round(node.y, 8))
        for node in second_result.nodes
    }

    assert first_positions == second_positions


def test_no_self_edges_or_duplicate_undirected_edges_are_produced() -> None:
    records = _sample_records()
    similarity_result = _similarity_result(
        [
            ("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-1", 0.99),
            ("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-2", 0.83),
            ("CSV_IMPORT:US-FIBER-2", "CSV_IMPORT:US-FIBER-1", 0.82),
        ]
    )

    result = PatentGraphBuilder().build(records, similarity_result, min_similarity=0.25)

    assert result.edge_count == 1
    assert all(
        edge.source_analysis_id != edge.target_analysis_id for edge in result.edges
    )
    assert [
        frozenset((edge.source_analysis_id, edge.target_analysis_id))
        for edge in result.edges
    ] == [frozenset(("CSV_IMPORT:US-FIBER-1", "CSV_IMPORT:US-FIBER-2"))]


def _similarity_result(
    edge_specs: list[tuple[str, str, float]],
) -> PatentSimilarityResult:
    return PatentSimilarityResult(
        edges=[
            PatentSimilarityEdge(
                source_analysis_id=source_analysis_id,
                target_analysis_id=target_analysis_id,
                similarity_score=similarity_score,
                source_patent_id=source_analysis_id.split(":", maxsplit=1)[1],
                target_patent_id=target_analysis_id.split(":", maxsplit=1)[1],
                source_title=source_analysis_id,
                target_title=target_analysis_id,
            )
            for source_analysis_id, target_analysis_id, similarity_score in edge_specs
        ],
        patents_analyzed=0,
        threshold=0.25,
        top_k=3,
    )


def _sample_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="US-FIBER-1",
            source=SourceType.CSV_IMPORT,
            title="Fiber sensor garment",
            abstract="fiber textile sensor garment",
            assignee="Fiber Labs",
            country="US",
            keywords=["fiber", "sensor"],
        ),
        PatentRecord(
            patent_id="US-FIBER-2",
            source=SourceType.CSV_IMPORT,
            title="Textile strain monitor",
            abstract="textile sensor strain monitor",
            assignee="Textile Systems",
            country="US",
            keywords=["textile", "sensor"],
        ),
        PatentRecord(
            patent_id="US-BATTERY-1",
            source=SourceType.JSON_IMPORT,
            title="Flexible battery pack",
            abstract="battery storage cell power",
            assignee="Power Weave",
            country="US",
            keywords=["battery", "power"],
        ),
    ]


def _duplicate_patent_id_records() -> list[PatentRecord]:
    return [
        PatentRecord(
            patent_id="DUPLICATE-1",
            source=SourceType.CSV_IMPORT,
            title="Fiber sensor garment",
            abstract="fiber textile sensor garment",
            assignee="Fiber Labs",
            country="US",
            keywords=["fiber"],
        ),
        PatentRecord(
            patent_id="DUPLICATE-1",
            source=SourceType.JSON_IMPORT,
            title="Fiber sensor garment alternate",
            abstract="fiber textile sensor garment alternate",
            assignee="Alt Fiber Labs",
            country="DE",
            keywords=["sensor"],
        ),
        PatentRecord(
            patent_id="US-UNIQUE-1",
            source=SourceType.CSV_IMPORT,
            title="Flexible connector textile",
            abstract="connector textile integration",
            assignee="Connector Works",
            country="GB",
            keywords=["connector"],
        ),
    ]
