from __future__ import annotations

import math
from pathlib import Path

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.contracts_v2 import (
    _adjusted_pvalue_status,
    _biological_threshold,
    _canonical_effect,
    _numerical_direction,
    _optional_float,
    _optional_str,
    _row_warnings,
    _source_row_identifier,
    _statistical_support,
    _status_from_column,
)


def test_optional_value_helpers_preserve_unknown_without_invention() -> None:
    assert _optional_float(None) is None
    assert _optional_float("") is None
    assert _optional_float("not-a-number") is None
    assert _optional_float(math.nan) is None
    assert _optional_float("2.5") == 2.5
    assert _optional_str(None) is None
    assert _optional_str("") is None
    assert _optional_str("nan") is None
    assert _optional_str("reported") == "reported"


def test_status_and_source_row_helpers_use_explicit_columns(tmp_path: Path) -> None:
    config = ExpressionConfig(
        backend="precomputed",
        count_matrix=tmp_path / "counts.tsv",
        sample_metadata=tmp_path / "samples.tsv",
        precomputed_table=tmp_path / "de.tsv",
        input_mode="precomputed_de",
        source_row_id_column="source_id",
    )
    row = {"gene": "TP53", "source_id": "row-7", "status": ""}
    assert _status_from_column(row, None, "tested") == "tested"
    assert _status_from_column(row, "status", "tested") == "imported_missing"
    assert _source_row_identifier(row, 7, config) == "row-7"
    fallback_config = config.model_copy(update={"source_row_id_column": None})
    assert _source_row_identifier({"gene": "TP53"}, 7, fallback_config) == "row:7:TP53"


def test_effect_status_helpers_are_state_specific() -> None:
    assert _canonical_effect(reported=1.0, shrunken=0.25) == (
        0.25,
        "imported_shrunken_log2fc",
    )
    assert _canonical_effect(reported=None, shrunken=None) == (None, "unavailable")
    assert _adjusted_pvalue_status(0.02, "not_filtered", "estimated") == (
        "adjusted_pvalue_available"
    )
    assert _adjusted_pvalue_status(None, "outlier_filtered", "estimated") == "outlier_filtered"
    assert _adjusted_pvalue_status(None, "not_filtered", "model_failure") == "model_failure"
    assert _adjusted_pvalue_status(None, "not_filtered", "estimated") == (
        "adjusted_pvalue_unavailable"
    )


def test_numerical_and_statistical_support_helpers_do_not_force_significance() -> None:
    assert _numerical_direction(1.0, "filtered_low_count", "estimated") == "untested"
    assert _numerical_direction(1.0, "tested", "model_failure") == "not_estimable"
    assert _numerical_direction(None, "tested", "estimated") == "uncertain"
    assert _numerical_direction(-1.0, "tested", "estimated") == "decreased"
    assert _numerical_direction(1.0, "tested", "estimated") == "increased"
    assert _numerical_direction(0.0, "tested", "estimated") == "exact_zero"
    assert _statistical_support(None, "not_tested", "not_filtered", "estimated", 0.05) == (
        "not_tested"
    )
    assert _statistical_support(None, "tested", "not_filtered", "model_failure", 0.05) == (
        "indeterminate"
    )
    assert _statistical_support(None, "tested", "unsupported", "estimated", 0.05) == ("unsupported")
    assert _statistical_support(None, "tested", "not_filtered", "estimated", 0.05) == (
        "adjusted_pvalue_unavailable"
    )
    assert _statistical_support(0.01, "tested", "not_filtered", "estimated", 0.05) == (
        "significant"
    )
    assert _statistical_support(0.20, "tested", "not_filtered", "estimated", 0.05) == (
        "not_significant"
    )


def test_biological_threshold_and_warning_helpers_preserve_absence(tmp_path: Path) -> None:
    assert _biological_threshold(None, 0.5) == "indeterminate"
    assert _biological_threshold(0.1, None) == "threshold_not_configured"
    assert _biological_threshold(-0.6, 0.5) == "exceeds_decrease_threshold"
    assert _biological_threshold(0.6, 0.5) == "exceeds_increase_threshold"
    assert _biological_threshold(0.1, 0.5) == "below_effect_threshold"
    missing_abundance_config = ExpressionConfig(
        backend="precomputed",
        count_matrix=tmp_path / "counts.tsv",
        sample_metadata=tmp_path / "samples.tsv",
        precomputed_table=tmp_path / "de.tsv",
        input_mode="precomputed_de",
    )
    assert _row_warnings(missing_abundance_config, {}, None) == (
        "condition-specific abundance summaries absent; values not invented",
        "shrunken log2FC unavailable; not copied from reported log2FC",
    )
    complete_config = missing_abundance_config.model_copy(
        update={
            "control_abundance_column": "control_mean",
            "treatment_abundance_column": "treated_mean",
        }
    )
    assert _row_warnings(complete_config, {}, 0.1) == ()
