from __future__ import annotations

import networkx as nx
import pandas as pd


def build_directed_graph(network: pd.DataFrame) -> nx.DiGraph[str]:
    graph: nx.DiGraph[str] = nx.DiGraph()
    for row in network.to_dict("records"):
        graph.add_edge(row["source"], row["target"], sign=row["sign"])
    return graph


def shortest_directed_path(
    graph: nx.DiGraph[str], source: str, target: str, max_length: int
) -> list[str] | None:
    try:
        path = nx.shortest_path(graph, source, target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
    return path if len(path) - 1 <= max_length else None
