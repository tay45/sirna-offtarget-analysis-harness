from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import pandas as pd

from sirna_offtarget.models import Direction, ExpressionResult, PathwayResult
from sirna_offtarget.pathway.network.models import (
    NormalizedMechanisticEdge,
    NormalizedMechanisticPath,
)
from sirna_offtarget.pathway.network.path_sign import (
    compose_signed_path,
    expected_after_target_decrease,
)
from sirna_offtarget.pathway.providers.models import ConsensusMechanisticEdgeRecord


@dataclass(frozen=True)
class NetworkTraceResult:
    pathway_results: dict[str, PathwayResult]
    edges: tuple[NormalizedMechanisticEdge, ...]
    paths: tuple[NormalizedMechanisticPath, ...]
    provider_evidence_edges: tuple[object, ...] = ()
    consensus_edges: tuple[ConsensusMechanisticEdgeRecord, ...] = ()


def trace_mechanistic_network(
    intended_target_gene: str,
    expression_results: dict[str, ExpressionResult],
    network: pd.DataFrame,
    regulons: pd.DataFrame,
    max_path_length: int,
    maximum_paths_per_candidate: int = 25,
) -> NetworkTraceResult:
    graph, edges = _build_graph(network)
    paths: list[NormalizedMechanisticPath] = []
    pathway_results: dict[str, PathwayResult] = {}
    for gene, expression in expression_results.items():
        candidate_paths = _candidate_paths(
            graph,
            intended_target_gene,
            gene,
            expression,
            max_path_length,
            maximum_paths_per_candidate,
        )
        paths.extend(candidate_paths)
        signed_expectations = {
            path.expected_candidate_direction_after_target_decrease
            for path in candidate_paths
            if path.expected_candidate_direction_after_target_decrease is not None
        }
        conflicting = len(signed_expectations) > 1
        consistent = [path for path in candidate_paths if path.direction_consistent is True]
        contradictory = [path for path in candidate_paths if path.direction_consistent is False]
        best = candidate_paths[0] if candidate_paths else None
        provider_sources = tuple(
            sorted({provider for path in candidate_paths for provider in path.provider_sources})
        )
        evidence_limitations: tuple[str, ...] = (
            ("conflicting signed paths retained",) if conflicting else ()
        )
        if best and not best.fully_signed:
            evidence_limitations += ("unsigned paths do not support directional claims",)
        expected_direction = (
            Direction(best.expected_candidate_direction_after_target_decrease)
            if best and best.expected_candidate_direction_after_target_decrease
            else None
        )
        pathway_results[gene] = PathwayResult(
            gene=gene,
            target_pathway_distance=best.path_length if best else None,
            direction_consistency=best.direction_consistent if best else None,
            pathway_coherence=_pathway_coherence(candidate_paths),
            regulon_evidence=_regulon_coherence(gene, regulons, expression_results),
            stress_signature_evidence=_stress_signature(gene, regulons),
            paths=best.ordered_nodes if best else (),
            shortest_signed_path=best.ordered_nodes if best and best.fully_signed else (),
            shortest_unsigned_supported_path=best.ordered_nodes if best else (),
            composed_path_sign=_sign_int(best.composed_sign) if best else None,
            expected_candidate_direction=expected_direction,
            conflicting_paths=conflicting,
            supporting_path_count=len(consistent),
            contradictory_path_count=len(contradictory),
            provider_sources=provider_sources,
            evidence_limitations=evidence_limitations,
        )
    return NetworkTraceResult(pathway_results, tuple(edges), tuple(paths))


def trace_consensus_mechanistic_network(
    intended_target_gene: str,
    expression_results: dict[str, ExpressionResult],
    consensus_edges: list[ConsensusMechanisticEdgeRecord],
    regulons: pd.DataFrame,
    max_path_length: int,
    maximum_paths_per_candidate: int = 25,
) -> NetworkTraceResult:
    network = pd.DataFrame(
        [
            {
                "source": edge.source,
                "target": edge.target,
                "sign": edge.consensus_sign,
                "provider": ",".join(edge.provider_sources),
                "references": ";".join(edge.references),
                "relation_type": edge.relation_type,
                "mechanism": edge.mechanism,
                "evidence_level": edge.evidence_level,
                "predicted_only": edge.predicted_only,
                "database_version": ";".join(edge.database_versions),
                "retrieval_snapshot": ";".join(edge.retrieval_snapshots),
                "directed": edge.directed,
                "causal_eligible": edge.causal_eligible,
                "functional_only": edge.functional_only,
                "consensus_edge_id": edge.edge_id,
                "lineage_key": ";".join(edge.lineage_groups),
            }
            for edge in consensus_edges
        ]
    )
    trace = trace_mechanistic_network(
        intended_target_gene,
        expression_results,
        network,
        regulons,
        max_path_length,
        maximum_paths_per_candidate,
    )
    return NetworkTraceResult(
        trace.pathway_results,
        trace.edges,
        trace.paths,
        consensus_edges=tuple(consensus_edges),
    )


def _build_graph(
    network: pd.DataFrame,
) -> tuple[nx.DiGraph[str], list[NormalizedMechanisticEdge]]:
    graph: nx.DiGraph[str] = nx.DiGraph()
    edges: list[NormalizedMechanisticEdge] = []
    for index, row in enumerate(network.to_dict("records"), start=1):
        source = str(row.get("source"))
        target = str(row.get("target"))
        sign = _normalize_sign(str(row.get("sign", "unknown")))
        provider = str(row.get("provider", "synthetic_snapshot"))
        references = (
            tuple(str(row.get("references", "")).split(";")) if row.get("references") else ()
        )
        edge = NormalizedMechanisticEdge(
            edge_id=str(row.get("consensus_edge_id") or f"edge_{index:05d}"),
            source=source,
            target=target,
            source_identifier=source,
            target_identifier=target,
            directed=bool(row.get("directed", True)),
            sign=sign,
            relation_type=str(row.get("relation_type", "regulates")),
            mechanism=str(row.get("mechanism", "provider_asserted_relation")),
            provider=provider,
            original_sources=(provider,),
            references=references,
            organism=str(row.get("organism", "human")),
            evidence_level=str(row.get("evidence_level", "fixture")),
            signed_support_count=0 if sign in {"unsigned", "unknown", "conflicting"} else 1,
            unsigned_support_count=1 if sign == "unsigned" else 0,
            source_count=len(str(row.get("lineage_key", "")).split(";"))
            if row.get("lineage_key")
            else 1,
            reference_count=len(references),
            predicted_only=bool(row.get("predicted_only", False)),
            conflict=sign == "conflicting",
            database_versions=(str(row.get("database_version", "synthetic_snapshot_v1")),),
            retrieval_snapshots=(str(row.get("retrieval_snapshot", "local_fixture")),),
            lineage_key=str(row.get("lineage_key") or f"{provider}:{source}:{target}:{sign}"),
            warnings=(),
        )
        graph.add_edge(source, target, edge=edge, sign=sign, provider=provider)
        edges.append(edge)
    return graph, edges


def _candidate_paths(
    graph: nx.DiGraph[str],
    intended_target: str,
    candidate: str,
    expression: ExpressionResult,
    max_length: int,
    limit: int,
) -> list[NormalizedMechanisticPath]:
    if intended_target == candidate:
        return []
    try:
        raw_paths = nx.all_simple_paths(graph, intended_target, candidate, cutoff=max_length)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []
    paths: list[NormalizedMechanisticPath] = []
    for index, nodes in enumerate(raw_paths, start=1):
        if index > limit:
            break
        edge_records = [
            graph.edges[left, right]["edge"] for left, right in zip(nodes, nodes[1:], strict=False)
        ]
        signs = [edge.sign for edge in edge_records]
        conflicting_edge_count = sum(1 for sign in signs if sign == "conflicting")
        composed = compose_signed_path(signs)
        expected = expected_after_target_decrease(composed)
        fully_signed = composed is not None
        direction_consistent = expected == expression.direction if expected is not None else None
        path_id = f"path_{candidate}_{index:03d}"
        composed_sign = "positive" if composed == 1 else "negative" if composed == -1 else None
        expected_direction = expected.value if expected else None
        paths.append(
            NormalizedMechanisticPath(
                path_id=path_id,
                intended_target=intended_target,
                candidate=candidate,
                ordered_nodes=tuple(nodes),
                ordered_edge_ids=tuple(edge.edge_id for edge in edge_records),
                path_length=len(nodes) - 1,
                directed=True,
                fully_signed=fully_signed,
                composed_sign=composed_sign,
                expected_candidate_direction_after_target_decrease=expected_direction,
                observed_candidate_direction=expression.direction.value,
                direction_consistent=direction_consistent,
                provider_sources=tuple(sorted({edge.provider for edge in edge_records})),
                references=tuple(sorted({ref for edge in edge_records for ref in edge.references})),
                evidence_score=round(1.0 / max(len(nodes) - 1, 1), 6),
                conflicting_with_other_paths=False,
                unsigned_edge_count=sum(1 for sign in signs if sign == "unsigned"),
                conflicting_edge_count=conflicting_edge_count,
                positive_composed_path_count=1 if composed == 1 else 0,
                negative_composed_path_count=1 if composed == -1 else 0,
                warnings=(
                    (
                        ("unsigned/unknown edge prevents directional expectation",)
                        if not fully_signed
                        else ()
                    )
                    + (
                        ("conflicting edge prevents directional expectation",)
                        if conflicting_edge_count
                        else ()
                    )
                ),
            )
        )
    expectations = {
        path.expected_candidate_direction_after_target_decrease
        for path in paths
        if path.expected_candidate_direction_after_target_decrease is not None
    }
    if len(expectations) > 1:
        paths = [
            NormalizedMechanisticPath(**{**path.__dict__, "conflicting_with_other_paths": True})
            for path in paths
        ]
    return sorted(paths, key=lambda path: (path.path_length, path.path_id))


def _pathway_coherence(paths: list[NormalizedMechanisticPath]) -> float:
    if not paths:
        return 0.0
    signed = sum(1 for path in paths if path.fully_signed)
    consistent = sum(1 for path in paths if path.direction_consistent is True)
    return round((signed + consistent) / (2 * len(paths)), 6)


def _regulon_coherence(
    gene: str,
    regulons: pd.DataFrame,
    expression_results: dict[str, ExpressionResult],
) -> float:
    memberships = [row for row in regulons.to_dict("records") if str(row.get("target", "")) == gene]
    if not memberships:
        return 0.0
    regulon = str(memberships[0].get("regulon", ""))
    targets = [
        str(row.get("target", ""))
        for row in regulons.to_dict("records")
        if str(row.get("regulon", "")) == regulon
    ]
    changed = [
        target
        for target in targets
        if target in expression_results
        and expression_results[target].direction.value in {"up", "down"}
    ]
    return round(len(changed) / len(targets), 6) if targets else 0.0


def _stress_signature(gene: str, regulons: pd.DataFrame) -> float:
    return (
        1.0
        if any(
            str(row.get("target", "")) == gene and str(row.get("regulon", "")) == "stress_signature"
            for row in regulons.to_dict("records")
        )
        else 0.0
    )


def _normalize_sign(sign: str) -> str:
    normalized = sign.lower()
    if normalized in {"activates", "activation", "positive", "+1", "stimulation"}:
        return "positive"
    if normalized in {"inhibits", "inhibition", "negative", "-1"}:
        return "negative"
    if normalized in {"conflict", "conflicting"}:
        return "conflicting"
    if normalized in {"unsigned", "functional"}:
        return "unsigned"
    return "unknown"


def _sign_int(sign: str | None) -> int | None:
    if sign == "positive":
        return 1
    if sign == "negative":
        return -1
    return None
