from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.models import ExpressionResult


@dataclass(frozen=True)
class ExpressionContrastRecordV1:
    contrast_id: str
    condition_column: str
    control_condition: str
    treatment_condition: str
    design_formula: str


@dataclass(frozen=True)
class ExpressionNormalizationRunRecordV1:
    normalization_run_id: str
    input_mode: str
    value_scale: str
    normalization_method: str
    differential_method: str
    effect_scale: str
    multiple_testing_method: str
    backend_name: str
    backend_version: str
    demonstration_only: bool


@dataclass(frozen=True)
class NormalizedGeneEffectRecordV1:
    gene: str
    gene_id_namespace: str
    organism: str
    contrast_id: str
    normalization_run_id: str
    canonical_log2_fold_change: float
    effect_scale: str
    direction: str
    threshold_status: str
    tested_status: str
    low_count_status: str
    raw_p_value: float | None
    adjusted_p_value: float | None
    significance_status: str
    backend_name: str
    backend_version: str
    demonstration_only: bool
    provenance: dict[str, str]


def build_contrast_record(config: ExpressionConfig) -> ExpressionContrastRecordV1:
    return ExpressionContrastRecordV1(
        contrast_id=config.contrast_id,
        condition_column=config.condition_column,
        control_condition=config.control_condition,
        treatment_condition=config.treatment_condition,
        design_formula=config.design_formula,
    )


def build_normalization_run_record(
    results: dict[str, ExpressionResult],
    config: ExpressionConfig,
) -> ExpressionNormalizationRunRecordV1:
    backend_name = "unexecuted"
    backend_version = "unknown"
    demonstration_only = False
    first = next(iter(results.values()), None)
    if first is not None:
        backend_name = first.backend_name
        backend_version = first.backend_version
        demonstration_only = first.demonstration_only
    basis = "|".join(
        [
            config.input_mode,
            config.value_scale,
            config.normalization_method,
            config.differential_method,
            config.effect_scale,
            config.contrast_id,
            backend_name,
            backend_version,
        ]
    )
    run_id = "exprnorm-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return ExpressionNormalizationRunRecordV1(
        normalization_run_id=run_id,
        input_mode=config.input_mode,
        value_scale=config.value_scale,
        normalization_method=config.normalization_method,
        differential_method=config.differential_method,
        effect_scale=config.effect_scale,
        multiple_testing_method=config.multiple_testing_method,
        backend_name=backend_name,
        backend_version=backend_version,
        demonstration_only=demonstration_only,
    )


def build_normalized_gene_effect_records(
    results: dict[str, ExpressionResult],
    config: ExpressionConfig,
    normalization_run: ExpressionNormalizationRunRecordV1,
    contrast: ExpressionContrastRecordV1,
    organism: str,
) -> list[NormalizedGeneEffectRecordV1]:
    records: list[NormalizedGeneEffectRecordV1] = []
    for gene in sorted(results):
        result = results[gene]
        effect = (
            result.shrunken_log2_fold_change if config.lfc_shrinkage else result.log2_fold_change
        )
        records.append(
            NormalizedGeneEffectRecordV1(
                gene=result.gene,
                gene_id_namespace=config.gene_id_namespace,
                organism=organism,
                contrast_id=contrast.contrast_id,
                normalization_run_id=normalization_run.normalization_run_id,
                canonical_log2_fold_change=effect,
                effect_scale=config.effect_scale,
                direction=direction_from_effect(effect),
                threshold_status=threshold_status(effect, config.absolute_log2_fold_change),
                tested_status="filtered_low_count" if result.low_count_flag else "tested",
                low_count_status="low_count" if result.low_count_flag else "passes_count_filter",
                raw_p_value=result.raw_p_value,
                adjusted_p_value=result.adjusted_p_value,
                significance_status=significance_status(
                    result.adjusted_p_value,
                    config.padj_threshold,
                    result.low_count_flag,
                ),
                backend_name=result.backend_name,
                backend_version=result.backend_version,
                demonstration_only=result.demonstration_only,
                provenance={
                    "input_mode": config.input_mode,
                    "value_scale": config.value_scale,
                    "normalization_method": config.normalization_method,
                    "differential_method": config.differential_method,
                    "p_value_status": result.p_value_status,
                    "shrinkage_status": result.shrinkage_status,
                },
            )
        )
    return records


def direction_from_effect(effect: float) -> str:
    if effect < 0:
        return "decreased"
    if effect > 0:
        return "increased"
    return "unchanged"


def threshold_status(effect: float, threshold: float) -> str:
    return "above_threshold" if abs(effect) >= threshold else "below_threshold"


def significance_status(
    adjusted_p_value: float | None,
    threshold: float,
    low_count_flag: bool,
) -> str:
    if low_count_flag:
        return "not_tested_low_count"
    if adjusted_p_value is None:
        return "adjusted_pvalue_unavailable"
    if adjusted_p_value <= threshold:
        return "significant"
    return "not_significant"


def records_as_dicts(records: list[Any]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]
