from __future__ import annotations

import math

import pandas as pd

from sirna_offtarget.config import ExpressionConfig

SUPPORTED_INPUT_MODES = {"raw_counts", "precomputed_de", "normalized_matrix"}
RAW_COUNT_SCALES = {"raw_count"}
NORMALIZED_SCALES = {
    "normalized_count",
    "log2_expression",
    "vst",
    "rlog",
    "voom_log_cpm",
    "tpm",
    "fpkm",
    "rpkm",
}
SUPPORTED_EFFECT_SCALES = {"log2_fold_change"}


def validate_expression_config(config: ExpressionConfig) -> None:
    if config.input_mode not in SUPPORTED_INPUT_MODES:
        raise ValueError(f"unsupported expression.input_mode {config.input_mode!r}")
    if config.effect_scale not in SUPPORTED_EFFECT_SCALES:
        raise ValueError(f"unsupported expression.effect_scale {config.effect_scale!r}")
    if config.duplicate_gene_policy != "reject":
        raise ValueError("expression.duplicate_gene_policy currently supports only 'reject'")
    if config.input_mode == "raw_counts" and config.value_scale not in RAW_COUNT_SCALES:
        raise ValueError("raw_counts input_mode requires expression.value_scale='raw_count'")
    if config.input_mode == "precomputed_de" and config.precomputed_table is None:
        raise ValueError("precomputed_de input_mode requires expression.precomputed_table")
    if config.input_mode == "normalized_matrix" and config.value_scale not in NORMALIZED_SCALES:
        raise ValueError("normalized_matrix input_mode requires a declared normalized value scale")
    if config.value_scale in {"tpm", "fpkm", "rpkm"} and config.input_mode == "raw_counts":
        raise ValueError(f"{config.value_scale} cannot be used as raw-count input")
    if not config.contrast_id:
        raise ValueError("expression.contrast_id must be non-empty")
    if config.control_condition == config.treatment_condition:
        raise ValueError("expression control and treatment conditions must differ")


def validate_raw_counts_input(
    counts: pd.DataFrame,
    metadata: pd.DataFrame,
    config: ExpressionConfig,
) -> None:
    validate_expression_config(config)
    if config.input_mode != "raw_counts":
        return
    if counts.empty:
        raise ValueError("raw_counts input requires a non-empty count matrix")
    if metadata.empty:
        raise ValueError("raw_counts input requires non-empty sample metadata")
    if counts.index.astype(str).duplicated().any():
        raise ValueError("count matrix contains duplicate gene identifiers")
    missing_metadata = {config.sample_column, config.condition_column}.difference(metadata.columns)
    if missing_metadata:
        raise ValueError(f"sample metadata missing required columns: {sorted(missing_metadata)}")
    samples = metadata[config.sample_column].astype(str)
    if samples.duplicated().any():
        duplicated = sorted(samples[samples.duplicated()].unique())
        raise ValueError(f"sample metadata contains duplicate samples: {duplicated}")
    missing_samples = sorted(set(samples).difference(counts.columns.astype(str)))
    if missing_samples:
        raise ValueError(
            f"sample metadata references samples absent from counts: {missing_samples}"
        )
    observed_conditions = set(metadata[config.condition_column].astype(str))
    for condition in (config.control_condition, config.treatment_condition):
        if condition not in observed_conditions:
            raise ValueError(f"sample metadata missing condition {condition!r}")
    numeric_counts = counts.apply(pd.to_numeric, errors="coerce")
    if numeric_counts.isna().any().any():
        raise ValueError("count matrix contains non-numeric values")
    if (numeric_counts < 0).any().any():
        raise ValueError("count matrix contains negative counts")
    non_integer = numeric_counts.map(lambda value: not math.isclose(float(value), round(value)))
    if non_integer.any().any():
        raise ValueError("raw_counts input requires integer count values")


def validate_precomputed_table(table: pd.DataFrame, config: ExpressionConfig) -> None:
    validate_expression_config(config)
    required = [
        config.gene_column,
        config.base_mean_column,
        config.log2_fold_change_column,
        config.adjusted_p_value_column,
    ]
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise ValueError(f"precomputed expression table missing required columns: {missing}")
    genes = table[config.gene_column].astype(str)
    if genes.duplicated().any():
        duplicated = sorted(genes[genes.duplicated()].unique())
        raise ValueError(f"precomputed expression table contains duplicate genes: {duplicated}")
    numeric = pd.to_numeric(table[config.base_mean_column], errors="coerce")
    if numeric.isna().any():
        raise ValueError(
            f"precomputed expression column {config.base_mean_column!r} contains missing values"
        )
    for column in (config.log2_fold_change_column,):
        numeric = pd.to_numeric(table[column], errors="coerce")
        nonmissing = table[column].notna()
        if numeric[nonmissing].isna().any():
            raise ValueError(f"precomputed expression column {column!r} contains nonnumeric values")
    for column in (config.p_value_column, config.adjusted_p_value_column):
        if column not in table.columns:
            continue
        numeric = pd.to_numeric(table[column], errors="coerce")
        present = numeric.dropna()
        if ((present < 0) | (present > 1)).any():
            raise ValueError(
                f"precomputed p-value column {column!r} contains values outside [0, 1]"
            )
