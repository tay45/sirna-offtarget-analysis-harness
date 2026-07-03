from __future__ import annotations

import pytest

from sirna_offtarget.execution.dag import (
    STAGE_NODES,
    StageNode,
    downstream_of,
    execution_plan,
    topological_sort,
)
from sirna_offtarget.execution.exceptions import DependencyError


def test_stage_dag_is_topologically_sorted() -> None:
    ordered = topological_sort()
    positions = {stage: index for index, stage in enumerate(ordered)}
    assert ordered[0] == "validate"
    assert ordered[-1] == "expected_direct_effect"
    for name, node in STAGE_NODES.items():
        for dependency in node.dependencies:
            assert positions[dependency] < positions[name]


def test_stage_dag_rejects_cycles() -> None:
    nodes = {
        "a": StageNode("a", "1", ("b",)),
        "b": StageNode("b", "1", ("a",)),
    }
    with pytest.raises(DependencyError):
        topological_sort(nodes)


def test_downstream_selection_is_transitive() -> None:
    affected = downstream_of("expression_analysis")
    assert "isoform_uncertainty" in affected
    assert "transcript_targetability_ratio" in affected
    assert "expected_direct_effect" in affected
    assert "sequence_analysis" not in affected


def test_until_stage_execution_plan_uses_transitive_prerequisites_only() -> None:
    assert execution_plan(until_stage="transcript_targetability_ratio") == [
        "validate",
        "prepare_inputs",
        "map_identifiers",
        "sequence_analysis",
        "expression_analysis",
        "isoform_uncertainty",
        "transcript_targetability",
        "transcript_targetability_ratio",
    ]


def test_until_expected_direct_effect_execution_plan_uses_transitive_prerequisites_only() -> None:
    assert execution_plan(until_stage="expected_direct_effect") == [
        "validate",
        "prepare_inputs",
        "map_identifiers",
        "sequence_analysis",
        "expression_analysis",
        "isoform_uncertainty",
        "transcript_targetability",
        "transcript_targetability_ratio",
        "expected_direct_effect",
    ]
