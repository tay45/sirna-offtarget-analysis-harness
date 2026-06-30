from __future__ import annotations

from pathlib import Path

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.contracts import build_normalization_run_record
from sirna_offtarget.models import Direction, ExpressionResult


def test_normalization_run_id_is_stable_and_records_provenance(tmp_path: Path) -> None:
    config = ExpressionConfig(
        backend="synthetic",
        count_matrix=tmp_path / "counts.tsv",
        sample_metadata=tmp_path / "samples.tsv",
        normalization_method="median_ratio",
        differential_method="synthetic_demo",
    )
    result = ExpressionResult(
        gene="A",
        baseline_expression=10,
        normalized_control_expression=10,
        normalized_treated_expression=20,
        log2_fold_change=1,
        shrunken_log2_fold_change=0.75,
        adjusted_p_value=0.03,
        replicate_consistency=1,
        direction=Direction.UP,
        low_count_flag=False,
    )
    first = build_normalization_run_record({"A": result}, config)
    second = build_normalization_run_record({"A": result}, config)
    assert first == second
    assert first.normalization_run_id.startswith("exprnorm-")
    assert first.normalization_method == "median_ratio"
    assert first.effect_scale == "log2_fold_change"


def test_empty_normalization_run_records_unexecuted_backend(tmp_path: Path) -> None:
    config = ExpressionConfig(
        backend="synthetic",
        count_matrix=tmp_path / "counts.tsv",
        sample_metadata=tmp_path / "samples.tsv",
    )
    record = build_normalization_run_record({}, config)
    assert record.backend_name == "unexecuted"
    assert record.backend_version == "unknown"
    assert not record.demonstration_only
