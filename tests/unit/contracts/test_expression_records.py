from __future__ import annotations

from sirna_offtarget.contracts.stage_results import ExpressionRecordV1


def test_expression_record_is_typed() -> None:
    record = ExpressionRecordV1(
        gene="GENE1",
        baseline_expression=10.0,
        normalized_control_expression=10.0,
        normalized_treated_expression=5.0,
        log2_fold_change=-1.0,
        shrunken_log2_fold_change=-0.8,
        adjusted_p_value=0.01,
        replicate_consistency=1.0,
        direction="down",
        low_count_flag=False,
        backend_name="synthetic",
        backend_version="1",
        design_formula="~ condition",
        shrinkage_status="heuristic",
        p_value_status="synthetic",
        demonstration_only=True,
    )
    assert record.gene == "GENE1"
