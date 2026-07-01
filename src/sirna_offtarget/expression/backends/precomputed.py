from __future__ import annotations

from pathlib import Path

import pandas as pd

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.backends.base import ExpressionBackendMetadata
from sirna_offtarget.models import ExpressionResult


class LegacyExpressionPathNotSupportedError(RuntimeError):
    pass


class PrecomputedDifferentialExpressionBackend:
    demonstration_only = False

    def __init__(self, table_path: Path, design_formula: str = "~ condition") -> None:
        self.table_path = table_path
        self._columns = {
            "gene": "gene",
            "base_mean": "baseline_expression",
            "log2_fold_change": "log2_fold_change",
            "shrunken_log2_fold_change": "shrunken_log2_fold_change",
            "standard_error": "standard_error",
            "raw_p_value": "raw_p_value",
            "adjusted_p_value": "adjusted_p_value",
        }
        self._thresholds = {
            "minimum_base_mean": 10.0,
            "absolute_log2_fold_change": 0.25,
        }
        self.metadata = ExpressionBackendMetadata(
            name="precomputed_differential_expression",
            version="user-supplied",
            demonstration_only=False,
            design_formula=design_formula,
            tested_gene_universe=(),
        )

    @classmethod
    def from_config(cls, config: ExpressionConfig) -> PrecomputedDifferentialExpressionBackend:
        if config.precomputed_table is None:
            raise ValueError("precomputed_table is required for the precomputed backend")
        backend = cls(config.precomputed_table, config.design_formula)
        backend._columns = {
            "gene": config.gene_column,
            "base_mean": config.base_mean_column,
            "log2_fold_change": config.log2_fold_change_column,
            "shrunken_log2_fold_change": config.shrunken_log2_fold_change_column,
            "standard_error": config.standard_error_column,
            "raw_p_value": config.p_value_column,
            "adjusted_p_value": config.adjusted_p_value_column,
        }
        backend._thresholds = {
            "minimum_base_mean": config.min_baseline_count,
            "absolute_log2_fold_change": config.absolute_log2_fold_change,
        }
        return backend

    def run(self, counts: pd.DataFrame, metadata: pd.DataFrame) -> dict[str, ExpressionResult]:
        raise LegacyExpressionPathNotSupportedError(
            "The legacy precomputed ExpressionResult backend is disabled because it can "
            "invent adjusted p-values, condition means, replicate consistency, and shrinkage. "
            "Use the committed Expression V2 precomputed importer instead."
        )
