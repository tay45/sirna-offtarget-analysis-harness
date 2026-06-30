from __future__ import annotations

import math

import pandas as pd

from sirna_offtarget.models import Direction, ExpressionResult


def differential_expression(
    normalized_counts: pd.DataFrame,
    metadata: pd.DataFrame,
    min_baseline_count: float,
    min_expressed_replicates: int,
) -> dict[str, ExpressionResult]:
    control_samples = metadata.loc[metadata["condition"] == "control", "sample"].tolist()
    treated_samples = metadata.loc[metadata["condition"] == "treated", "sample"].tolist()
    results: dict[str, ExpressionResult] = {}
    for gene, row in normalized_counts.iterrows():
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
        effect = abs(shrunken)
        padj = max(0.0001, min(1.0, math.exp(-effect * 3.0)))
        signs = [math.copysign(1, t - c) for t, c in zip(treated, control, strict=False)]
        replicate_consistency = abs(sum(signs)) / len(signs) if signs else 0.0
        expressed_reps = int((control >= min_baseline_count).sum())
        low_count = baseline < min_baseline_count or expressed_reps < min_expressed_replicates
        results[str(gene)] = ExpressionResult(
            gene=str(gene),
            baseline_expression=round(baseline, 6),
            normalized_control_expression=round(baseline, 6),
            normalized_treated_expression=round(treated_mean, 6),
            log2_fold_change=round(lfc, 6),
            shrunken_log2_fold_change=round(shrunken, 6),
            adjusted_p_value=round(padj, 6),
            replicate_consistency=round(replicate_consistency, 6),
            direction=direction,
            low_count_flag=low_count,
        )
    return results
