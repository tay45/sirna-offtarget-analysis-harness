from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.api import analyze_expression_with_config
from sirna_offtarget.expression.validation import (
    validate_expression_config,
    validate_precomputed_table,
    validate_raw_counts_input,
)


def _config(tmp_path: Path, **updates: object) -> ExpressionConfig:
    values = {
        "backend": "synthetic",
        "count_matrix": tmp_path / "counts.tsv",
        "sample_metadata": tmp_path / "samples.tsv",
    }
    values.update(updates)
    return ExpressionConfig(**values)


def test_raw_counts_rejects_normalized_value_scale(tmp_path: Path) -> None:
    config = _config(tmp_path, value_scale="tpm")
    with pytest.raises(ValueError, match="requires expression.value_scale='raw_count'"):
        validate_raw_counts_input(pd.DataFrame({"s1": [1]}, index=["A"]), pd.DataFrame(), config)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"input_mode": "mystery"}, "unsupported expression.input_mode"),
        ({"effect_scale": "fold_change"}, "unsupported expression.effect_scale"),
        ({"duplicate_gene_policy": "first"}, "supports only 'reject'"),
        ({"input_mode": "precomputed_de"}, "requires expression.precomputed_table"),
        (
            {"input_mode": "normalized_matrix", "value_scale": "raw_count"},
            "requires a declared normalized value scale",
        ),
        ({"contrast_id": ""}, "contrast_id must be non-empty"),
        ({"control_condition": "same", "treatment_condition": "same"}, "must differ"),
    ],
)
def test_expression_config_validation_error_states(
    tmp_path: Path,
    updates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_expression_config(_config(tmp_path, **updates))


@pytest.mark.parametrize(
    ("counts", "metadata", "message"),
    [
        (pd.DataFrame(), pd.DataFrame(), "non-empty count matrix"),
        (pd.DataFrame({"c1": [1]}, index=["A"]), pd.DataFrame(), "non-empty sample metadata"),
        (
            pd.DataFrame({"c1": [1], "t1": [2]}, index=["A", "A"]),
            pd.DataFrame({"sample": ["c1", "t1"], "condition": ["control", "treated"]}),
            "duplicate gene identifiers",
        ),
        (
            pd.DataFrame({"c1": [1], "t1": [2]}, index=["A"]),
            pd.DataFrame({"sample": ["c1", "t1"]}),
            "missing required columns",
        ),
        (
            pd.DataFrame({"c1": [1], "t1": [2]}, index=["A"]),
            pd.DataFrame({"sample": ["c1", "c1"], "condition": ["control", "treated"]}),
            "duplicate samples",
        ),
        (
            pd.DataFrame({"c1": [1], "t1": [2]}, index=["A"]),
            pd.DataFrame({"sample": ["c1", "x"], "condition": ["control", "treated"]}),
            "absent from counts",
        ),
        (
            pd.DataFrame({"c1": [1], "t1": [2]}, index=["A"]),
            pd.DataFrame({"sample": ["c1", "t1"], "condition": ["control", "control"]}),
            "missing condition 'treated'",
        ),
        (
            pd.DataFrame({"c1": ["bad"], "t1": [2]}, index=["A"]),
            pd.DataFrame({"sample": ["c1", "t1"], "condition": ["control", "treated"]}),
            "non-numeric values",
        ),
        (
            pd.DataFrame({"c1": [-1], "t1": [2]}, index=["A"]),
            pd.DataFrame({"sample": ["c1", "t1"], "condition": ["control", "treated"]}),
            "negative counts",
        ),
    ],
)
def test_raw_count_validation_rejects_invalid_inputs(
    tmp_path: Path,
    counts: pd.DataFrame,
    metadata: pd.DataFrame,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_raw_counts_input(counts, metadata, _config(tmp_path))


def test_non_raw_input_skips_raw_count_matrix_checks(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        input_mode="normalized_matrix",
        value_scale="log2_expression",
    )
    validate_raw_counts_input(pd.DataFrame(), pd.DataFrame(), config)


def test_raw_counts_rejects_non_integer_values(tmp_path: Path) -> None:
    counts = pd.DataFrame({"c1": [10.5], "t1": [12]}, index=["GENE1"])
    metadata = pd.DataFrame({"sample": ["c1", "t1"], "condition": ["control", "treated"]})
    with pytest.raises(ValueError, match="integer count values"):
        validate_raw_counts_input(counts, metadata, _config(tmp_path))


def test_synthetic_backend_uses_declared_contrast_columns(tmp_path: Path) -> None:
    counts = pd.DataFrame({"ctrl": [100, 100], "drug": [25, 200]}, index=["A", "B"])
    metadata = pd.DataFrame({"sample_id": ["ctrl", "drug"], "arm": ["vehicle", "siRNA"]})
    results = analyze_expression_with_config(
        counts,
        metadata,
        _config(
            tmp_path,
            sample_column="sample_id",
            condition_column="arm",
            control_condition="vehicle",
            treatment_condition="siRNA",
            contrast_id="siRNA_vs_vehicle",
        ),
    )
    assert results["A"].log2_fold_change < 0
    assert results["B"].log2_fold_change > 0


@pytest.mark.parametrize(
    ("table", "message"),
    [
        (pd.DataFrame({"gene": ["A"]}), "missing required columns"),
        (
            pd.DataFrame(
                {
                    "gene": ["A", "A"],
                    "baseMean": [10, 11],
                    "log2FoldChange": [1, 2],
                    "padj": [0.1, 0.2],
                }
            ),
            "duplicate genes",
        ),
        (
            pd.DataFrame({"gene": ["A"], "baseMean": [None], "log2FoldChange": [1], "padj": [0.1]}),
            "contains missing values",
        ),
        (
            pd.DataFrame(
                {
                    "gene": ["A"],
                    "baseMean": [10],
                    "log2FoldChange": [1],
                    "pvalue": [1.2],
                    "padj": [0.1],
                }
            ),
            "outside \\[0, 1\\]",
        ),
    ],
)
def test_precomputed_table_validation_error_states(
    tmp_path: Path,
    table: pd.DataFrame,
    message: str,
) -> None:
    config = _config(
        tmp_path,
        backend="precomputed",
        input_mode="precomputed_de",
        precomputed_table=tmp_path / "de.tsv",
    )
    with pytest.raises(ValueError, match=message):
        validate_precomputed_table(table, config)


def test_precomputed_table_validation_accepts_missing_raw_p_column(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        backend="precomputed",
        input_mode="precomputed_de",
        precomputed_table=tmp_path / "de.tsv",
    )
    validate_precomputed_table(
        pd.DataFrame({"gene": ["A"], "baseMean": [10], "log2FoldChange": [1], "padj": [0.1]}),
        config,
    )


def test_expression_backend_error_routes_validate_explicit_backends(tmp_path: Path) -> None:
    counts = pd.DataFrame({"c1": [10], "t1": [20]}, index=["A"])
    metadata = pd.DataFrame({"sample": ["c1", "t1"], "condition": ["control", "treated"]})
    with pytest.raises(ValueError, match="must be explicitly set"):
        analyze_expression_with_config(counts, metadata, _config(tmp_path, backend=None))
    with pytest.raises(RuntimeError, match="raw_count_production_backend_unavailable"):
        analyze_expression_with_config(counts, metadata, _config(tmp_path, backend="deseq2_r"))
    with pytest.raises(ValueError, match="unsupported expression.backend"):
        analyze_expression_with_config(counts, metadata, _config(tmp_path, backend="unknown"))
