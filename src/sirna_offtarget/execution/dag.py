from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from sirna_offtarget.execution.exceptions import DependencyError, InvalidStageError


@dataclass(frozen=True)
class StageNode:
    name: str
    version: str
    data_dependencies: tuple[str, ...]
    completion_dependencies: tuple[str, ...] = ()
    optional: bool = False

    @property
    def dependencies(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.data_dependencies, *self.completion_dependencies)))


STAGE_ORDER: tuple[str, ...] = (
    "validate",
    "prepare_inputs",
    "map_identifiers",
    "sequence_analysis",
    "expression_analysis",
    "isoform_uncertainty",
    "transcript_targetability",
    "transcript_targetability_ratio",
)


STAGE_NODES: dict[str, StageNode] = {
    "validate": StageNode("validate", "1.0", ()),
    "prepare_inputs": StageNode("prepare_inputs", "1.0", (), ("validate",)),
    "map_identifiers": StageNode("map_identifiers", "1.0", (), ("prepare_inputs",)),
    "sequence_analysis": StageNode(
        "sequence_analysis", "1.0", (), ("prepare_inputs", "map_identifiers")
    ),
    "expression_analysis": StageNode(
        "expression_analysis", "1.0", (), ("prepare_inputs", "map_identifiers")
    ),
    "isoform_uncertainty": StageNode(
        "isoform_uncertainty", "1.0", ("expression_analysis",), ("map_identifiers",)
    ),
    "transcript_targetability": StageNode(
        "transcript_targetability",
        "1.0",
        ("isoform_uncertainty",),
        ("sequence_analysis", "map_identifiers"),
    ),
    "transcript_targetability_ratio": StageNode(
        "transcript_targetability_ratio",
        "1.0",
        ("isoform_uncertainty", "transcript_targetability"),
    ),
}


def topological_sort(nodes: dict[str, StageNode] | None = None) -> list[str]:
    graph = nodes or STAGE_NODES
    indegree = dict.fromkeys(graph, 0)
    children: dict[str, list[str]] = defaultdict(list)
    for name, node in graph.items():
        for dependency in node.dependencies:
            if dependency not in graph:
                raise DependencyError(f"{name} depends on unknown stage {dependency}")
            indegree[name] += 1
            children[dependency].append(name)
    queue = deque([name for name in STAGE_ORDER if name in graph and indegree[name] == 0])
    ordered: list[str] = []
    while queue:
        name = queue.popleft()
        ordered.append(name)
        for child in children[name]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(ordered) != len(graph):
        raise DependencyError("stage DAG contains a circular dependency")
    return ordered


def transitive_prerequisites(
    stage_name: str, nodes: dict[str, StageNode] | None = None
) -> set[str]:
    graph = nodes or STAGE_NODES
    if stage_name not in graph:
        raise InvalidStageError(stage_name)
    required: set[str] = set()

    def visit(name: str) -> None:
        for dependency in graph[name].dependencies:
            if dependency not in graph:
                raise DependencyError(f"{name} depends on unknown stage {dependency}")
            if dependency not in required:
                required.add(dependency)
                visit(dependency)

    visit(stage_name)
    return required


def execution_plan(
    *, until_stage: str | None = None, nodes: dict[str, StageNode] | None = None
) -> list[str]:
    graph = nodes or STAGE_NODES
    ordered = topological_sort(graph)
    if until_stage is None:
        return ordered
    required = transitive_prerequisites(until_stage, graph) | {until_stage}
    return [stage for stage in ordered if stage in required]


def downstream_of(stage_name: str, nodes: dict[str, StageNode] | None = None) -> set[str]:
    graph = nodes or STAGE_NODES
    if stage_name not in graph:
        raise InvalidStageError(stage_name)
    downstream: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name, node in graph.items():
            if name in downstream:
                continue
            if stage_name in node.dependencies or downstream.intersection(node.dependencies):
                downstream.add(name)
                changed = True
    return downstream


def stage_index(stage_name: str) -> int:
    if stage_name not in STAGE_ORDER:
        raise InvalidStageError(stage_name)
    return STAGE_ORDER.index(stage_name) + 1
