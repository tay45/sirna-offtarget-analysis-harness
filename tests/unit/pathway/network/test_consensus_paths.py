from __future__ import annotations

import pandas as pd

from sirna_offtarget.models import Direction, ExpressionResult
from sirna_offtarget.pathway.network import trace_consensus_mechanistic_network
from sirna_offtarget.pathway.providers.models import ConsensusMechanisticEdgeRecord


def expr(direction: Direction) -> ExpressionResult:
    return ExpressionResult("G", 100, 100, 50, -1, -0.8, 0.01, 1.0, direction, False)


def edge(edge_id: str, source: str, target: str, sign: str) -> ConsensusMechanisticEdgeRecord:
    return ConsensusMechanisticEdgeRecord(
        edge_id=edge_id,
        source=source,
        target=target,
        directed=True,
        consensus_sign=sign,
        relation_type="interaction",
        mechanism="test",
        provider_sources=("fixture",),
        references=("PMID",),
        evidence_ids=(edge_id,),
        lineage_groups=(edge_id,),
        independent_source_count=1,
        reference_count=1,
        positive_support=1 if sign == "positive" else 0,
        negative_support=1 if sign == "negative" else 0,
        unsigned_support=1 if sign == "unsigned" else 0,
        conflicting_support=1 if sign == "conflicting" else 0,
        evidence_level="curated",
        functional_only=sign == "unsigned",
        causal_eligible=sign in {"positive", "negative"},
        predicted_only=False,
        database_versions=("v",),
        retrieval_snapshots=("snap",),
    )


def test_path_sign_uses_all_edges_and_unsigned_has_no_direction() -> None:
    trace = trace_consensus_mechanistic_network(
        "T",
        {"G": expr(Direction.UP), "U": expr(Direction.DOWN)},
        [
            edge("e1", "T", "M", "positive"),
            edge("e2", "M", "G", "negative"),
            edge("e3", "T", "U", "unsigned"),
        ],
        pd.DataFrame(),
        4,
    )
    signed = trace.pathway_results["G"]
    unsigned = trace.pathway_results["U"]
    assert signed.composed_path_sign == -1
    assert signed.direction_consistency is True
    assert unsigned.expected_candidate_direction is None
    assert trace.paths[-1].unsigned_edge_count == 1
