from __future__ import annotations

import math

import pandas as pd

from sirna_offtarget.expression.backends.base import ExpressionBackendMetadata
from sirna_offtarget.expression.normalization import median_ratio_normalize
from sirna_offtarget.models import Direction, ExpressionResult


class SyntheticDemonstrationBackend:
    demonstration_only = True

    def __init__(
        self,
        min_baseline_count: float,
        min_expressed_replicates: int,
        *,
        sample_column: str = "sample",
        condition_column: str = "condition",
        control_condition: str = "control",
        treatment_condition: str = "treated",
    ) -> None:
        self.min_baseline_count = min_baseline_count
        self.min_expressed_replicates = min_expressed_replicates
        self.sample_column = sample_column
        self.condition_column = condition_column
        self.control_condition = control_condition
        self.treatment_condition = treatment_condition
        self.metadata = ExpressionBackendMetadata(
            name="synthetic_demonstration_backend",
            version="internal-v1",
            demonstration_only=True,
            design_formula="~ condition",
            tested_gene_universe=(),
        )

    def run(self, counts: pd.DataFrame, metadata: pd.DataFrame) -> dict[str, ExpressionResult]:
        normalized_counts = median_ratio_normalize(counts)
        control_samples = metadata.loc[
            metadata[self.condition_column] == self.control_condition,
            self.sample_column,
        ].tolist()
        treated_samples = metadata.loc[
            metadata[self.condition_column] == self.treatment_condition,
            self.sample_column,
        ].tolist()
        results: dict[str, ExpressionResult] = {}
        universe: list[str] = []
        for gene, row in normalized_counts.iterrows():
            universe.append(str(gene))
            control = row[control_samples].astype(float)
            treated = row[treated_samples].astype(float)
            baseline = float(control.mean())
            treated_mean = float(treated.mean())
            lfc = math.log2((treated_mean + 1.0) / (baseline + 1.0))
            shrunken = lfc * min(abs(lfc) / (abs(lfc) + 0.35), 1.0)
            direction = (
                Direction.DOWN
                if shrunken < -0.25
                else Direction.UP
                if shrunken > 0.25
                else Direction.UNCHANGED
            )
            synthetic_effect_q = max(0.0001, min(1.0, math.exp(-abs(shrunken) * 3.0)))
            signs = [math.copysign(1, t - c) for t, c in zip(treated, control, strict=False)]
            replicate_consistency = abs(sum(signs)) / len(signs) if signs else 0.0
            expressed_reps = int((control >= self.min_baseline_count).sum())
            low_count = (
                baseline < self.min_baseline_count or expressed_reps < self.min_expressed_replicates
            )
            results[str(gene)] = ExpressionResult(
                gene=str(gene),
                baseline_expression=round(baseline, 6),
                normalized_control_expression=round(baseline, 6),
                normalized_treated_expression=round(treated_mean, 6),
                log2_fold_change=round(lfc, 6),
                shrunken_log2_fold_change=round(shrunken, 6),
                adjusted_p_value=round(synthetic_effect_q, 6),
                replicate_consistency=round(replicate_consistency, 6),
                direction=direction,
                low_count_flag=low_count,
                backend_name=self.metadata.name,
                backend_version=self.metadata.version,
                design_formula=self.metadata.design_formula,
                shrinkage_status="heuristic_demo_shrinkage",
                standard_error=None,
                raw_p_value=None,
                p_value_status="synthetic_effect_q_value_not_statistical_p_value",
                demonstration_only=True,
            )
        self.metadata = ExpressionBackendMetadata(
            name=self.metadata.name,
            version=self.metadata.version,
            demonstration_only=True,
            design_formula=self.metadata.design_formula,
            tested_gene_universe=tuple(universe),
        )
        return results
