from __future__ import annotations

import pandas as pd

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.backends.base import ExpressionBackend
from sirna_offtarget.expression.backends.deseq2_r import Deseq2RBackend
from sirna_offtarget.expression.backends.precomputed import PrecomputedDifferentialExpressionBackend
from sirna_offtarget.expression.backends.pydeseq2 import PyDeseq2Backend
from sirna_offtarget.expression.backends.synthetic import SyntheticDemonstrationBackend
from sirna_offtarget.expression.normalization import median_ratio_normalize
from sirna_offtarget.expression.support import expression_execution_support
from sirna_offtarget.expression.validation import (
    validate_expression_config,
    validate_raw_counts_input,
)
from sirna_offtarget.models import ExpressionResult


def analyze_expression(
    counts: pd.DataFrame,
    metadata: pd.DataFrame,
    min_baseline_count: float,
    min_expressed_replicates: int,
) -> dict[str, ExpressionResult]:
    backend = SyntheticDemonstrationBackend(min_baseline_count, min_expressed_replicates)
    return backend.run(counts, metadata)


def analyze_expression_with_config(
    counts: pd.DataFrame,
    metadata: pd.DataFrame,
    config: ExpressionConfig,
) -> dict[str, ExpressionResult]:
    backend_name = config.backend
    if backend_name is None:
        raise ValueError(
            "expression.backend must be explicitly set; use precomputed, pydeseq2, "
            "deseq2_r, or synthetic_demo"
        )
    normalized = backend_name.lower().replace("-", "_")
    support = expression_execution_support(config)
    if support.failure_behavior == "normalized_matrix_execution_not_supported":
        raise RuntimeError("normalized_matrix_execution_not_supported")
    if support.failure_behavior == "raw_count_production_backend_unavailable":
        raise RuntimeError("raw_count_production_backend_unavailable")
    backend: ExpressionBackend
    if normalized in {"synthetic", "synthetic_demo"}:
        validate_raw_counts_input(counts, metadata, config)
        backend = SyntheticDemonstrationBackend(
            config.min_baseline_count,
            config.min_expressed_replicates,
            sample_column=config.sample_column,
            condition_column=config.condition_column,
            control_condition=config.control_condition,
            treatment_condition=config.treatment_condition,
        )
        return backend.run(counts, metadata)
    if normalized == "precomputed":
        if config.precomputed_table is None:
            raise ValueError("expression.precomputed_table is required for backend=precomputed")
        resolved = config
        if config.input_mode == "raw_counts":
            resolved = config.model_copy(update={"input_mode": "precomputed_de"})
        validate_expression_config(resolved)
        backend = PrecomputedDifferentialExpressionBackend.from_config(resolved)
        return backend.run(counts, metadata)
    if normalized == "pydeseq2":
        validate_raw_counts_input(counts, metadata, config)
        return PyDeseq2Backend(config).run(counts, metadata)
    if normalized == "deseq2_r":
        validate_raw_counts_input(counts, metadata, config)
        return Deseq2RBackend(config).run(counts, metadata)
    raise ValueError(f"unsupported expression.backend {backend_name!r}")


__all__ = ["analyze_expression", "analyze_expression_with_config", "median_ratio_normalize"]
