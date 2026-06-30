from __future__ import annotations

from sirna_offtarget.contracts.registry import STAGE_CONTRACTS
from sirna_offtarget.contracts.stage_results import ExpressionAnalysisResultV2


def test_expression_stage_returns_v2_contract() -> None:
    assert STAGE_CONTRACTS["expression_analysis"] is ExpressionAnalysisResultV2


def test_v1_is_not_stage_output() -> None:
    assert STAGE_CONTRACTS["expression_analysis"].expected_contract_name != (
        "ExpressionAnalysisResultV1"
    )
