from __future__ import annotations

import pandas as pd

from sirna_offtarget.models import ExpressionResult, PathwayResult
from sirna_offtarget.pathway.directed_paths import build_directed_graph, shortest_directed_path
from sirna_offtarget.pathway.enrichment import analyze_pathway_enrichment
from sirna_offtarget.pathway.network import NetworkTraceResult, trace_mechanistic_network


def analyze_pathways(
    intended_target_gene: str,
    expression_results: dict[str, ExpressionResult],
    network: pd.DataFrame,
    regulons: pd.DataFrame,
    max_path_length: int,
) -> dict[str, PathwayResult]:
    return trace_mechanistic_network(
        intended_target_gene,
        expression_results,
        network,
        regulons,
        max_path_length,
    ).pathway_results


__all__ = [
    "NetworkTraceResult",
    "analyze_pathway_enrichment",
    "analyze_pathways",
    "build_directed_graph",
    "shortest_directed_path",
    "trace_mechanistic_network",
]
