from __future__ import annotations

from pathlib import Path

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.contracts import (
    build_contrast_record,
    build_normalization_run_record,
    build_normalized_gene_effect_records,
)
from sirna_offtarget.models import Direction, ExpressionResult


def _config(tmp_path: Path) -> ExpressionConfig:
    return ExpressionConfig(
        backend="precomputed",
        count_matrix=tmp_path / "counts.tsv",
        sample_metadata=tmp_path / "samples.tsv",
        precomputed_table=tmp_path / "de.tsv",
        input_mode="precomputed_de",
        absolute_log2_fold_change=0.5,
    )


def _result(gene: str, lfc: float, padj: float, low_count: bool = False) -> ExpressionResult:
    return ExpressionResult(
        gene=gene,
        baseline_expression=20,
        normalized_control_expression=20,
        normalized_treated_expression=10,
        log2_fold_change=lfc,
        shrunken_log2_fold_change=lfc,
        adjusted_p_value=padj,
        replicate_consistency=1,
        direction=Direction.UNCHANGED,
        low_count_flag=low_count,
        backend_name="precomputed_differential_expression",
        backend_version="user-supplied",
        shrinkage_status="precomputed",
        raw_p_value=padj,
        p_value_status="user_supplied_statistical_result",
        demonstration_only=False,
    )


def test_negative_nonsignificant_effect_stays_decreased(tmp_path: Path) -> None:
    config = _config(tmp_path)
    results = {"A": _result("A", -0.7, 0.8)}
    run = build_normalization_run_record(results, config)
    contrast = build_contrast_record(config)
    record = build_normalized_gene_effect_records(results, config, run, contrast, "human")[0]
    assert record.direction == "decreased"
    assert record.threshold_status == "above_threshold"
    assert record.significance_status == "not_significant"


def test_low_count_is_not_labeled_nonsignificant(tmp_path: Path) -> None:
    config = _config(tmp_path)
    results = {"A": _result("A", -0.2, 0.9, low_count=True)}
    run = build_normalization_run_record(results, config)
    contrast = build_contrast_record(config)
    record = build_normalized_gene_effect_records(results, config, run, contrast, "human")[0]
    assert record.tested_status == "filtered_low_count"
    assert record.low_count_status == "low_count"
    assert record.significance_status == "not_tested_low_count"


def test_unavailable_adjusted_pvalue_and_zero_effect_states(tmp_path: Path) -> None:
    config = _config(tmp_path).model_copy(update={"lfc_shrinkage": False})
    result = _result("A", 0.0, 0.9)
    result = result.__class__(**{**result.__dict__, "adjusted_p_value": None})
    run = build_normalization_run_record({"A": result}, config)
    contrast = build_contrast_record(config)
    record = build_normalized_gene_effect_records({"A": result}, config, run, contrast, "human")[0]
    assert record.direction == "unchanged"
    assert record.threshold_status == "below_threshold"
    assert record.significance_status == "adjusted_pvalue_unavailable"
