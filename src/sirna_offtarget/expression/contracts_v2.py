from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.status_policy import normalize_imported_status
from sirna_offtarget.expression.support import ExpressionExecutionSupportRecord
from sirna_offtarget.identifiers.resolver_v2 import IdentifierResolutionRecordV2
from sirna_offtarget.models import ExpressionResult

SCHEMA_VERSION = "2"


@dataclass(frozen=True)
class ExpressionContrastRecordV2:
    schema_version: str
    contrast_id: str
    treatment_condition: str
    control_condition: str
    condition_column: str
    coefficient_or_contrast_definition: str
    design_formula: str
    covariates: tuple[str, ...]
    batch_terms: tuple[str, ...]
    paired_status: str
    reference_level: str | None
    biological_interpretation: str
    source_configuration_hash: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExpressionNormalizationRunRecordV2:
    schema_version: str
    normalization_run_id: str
    input_mode: str
    execution_support_level: str
    input_files: tuple[str, ...]
    input_checksums: dict[str, str]
    sample_metadata_file: str
    sample_metadata_checksum: str | None
    source_result_checksum: str | None
    organism: str
    gene_id_namespace: str
    identifier_snapshot_id: str | None
    sample_count: int
    condition_count: int
    replicate_counts: dict[str, int]
    design_formula: str
    contrasts: tuple[str, ...]
    covariates: tuple[str, ...]
    batch_terms: tuple[str, ...]
    normalization_method: str
    normalization_parameters: dict[str, Any]
    filtering_method: str
    filtering_parameters: dict[str, Any]
    differential_method: str
    differential_parameters: dict[str, Any]
    shrinkage_method: str
    shrinkage_status: str
    multiple_testing_method: str
    software: str
    software_version: str
    adapter_name: str
    adapter_version: str
    execution_command_or_api: str
    execution_environment: dict[str, str]
    started_at: str | None
    completed_at: str | None
    status: str
    output_checksums: dict[str, str]
    warnings: tuple[str, ...]
    identifier_snapshot_checksum: str | None = None
    resolver_version: str = "IdentifierResolverV2"
    identifier_ambiguity_policy: str = "exclude"
    identifier_snapshot_verified: bool = False


@dataclass(frozen=True)
class NormalizedGeneEffectRecordV2:
    schema_version: str
    record_id: str
    original_gene_id: str
    original_gene_namespace: str
    canonical_gene_id: str | None
    approved_symbol: str | None
    identifier_resolution_id: str
    identifier_mapping_confidence: float
    identifier_ambiguity_status: str
    identifier_organism_match: bool
    organism: str
    contrast_id: str
    normalization_run_id: str
    input_mode: str
    input_value_scale: str
    normalization_method: str
    differential_method: str
    effect_scale: str
    raw_effect_estimate: float | None
    reported_log2_fold_change: float | None
    shrunken_log2_fold_change: float | None
    canonical_log2_fold_change: float | None
    canonical_effect_source: str
    standard_error: float | None
    confidence_interval_lower: float | None
    confidence_interval_upper: float | None
    test_statistic: float | None
    raw_p_value: float | None
    adjusted_p_value: float | None
    adjusted_pvalue_status: str
    multiple_testing_method: str
    tested_status: str
    filter_status: str
    low_count_status: str
    model_status: str
    exclusion_reason: str | None
    numerical_direction: str
    statistical_support_status: str
    biological_threshold_status: str
    direction_basis: str
    control_abundance_summary: float | None
    treatment_abundance_summary: float | None
    mean_abundance_summary: float | None
    replicate_count_control: int | None
    replicate_count_treatment: int | None
    design_formula: str
    covariates: tuple[str, ...]
    batch_terms: tuple[str, ...]
    analysis_software: str
    analysis_software_version: str
    provenance_record_ids: tuple[str, ...]
    source_row_identifier: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


def build_expression_contrast_record_v2(config: ExpressionConfig) -> ExpressionContrastRecordV2:
    return ExpressionContrastRecordV2(
        schema_version=SCHEMA_VERSION,
        contrast_id=config.contrast_id,
        treatment_condition=config.treatment_condition,
        control_condition=config.control_condition,
        condition_column=config.condition_column,
        coefficient_or_contrast_definition=(
            f"{config.treatment_condition} - {config.control_condition}"
        ),
        design_formula=config.design_formula,
        covariates=(),
        batch_terms=(),
        paired_status="unpaired",
        reference_level=config.control_condition,
        biological_interpretation="positive log2FC means treatment exceeds control",
        source_configuration_hash=_hash_data(
            {
                "contrast_id": config.contrast_id,
                "treatment": config.treatment_condition,
                "control": config.control_condition,
                "design": config.design_formula,
            }
        ),
    )


def build_expression_normalization_run_record_v2(
    *,
    config: ExpressionConfig,
    organism: str,
    support: ExpressionExecutionSupportRecord,
    counts_path: Path,
    metadata_path: Path,
    source_result_path: Path | None,
    metadata: pd.DataFrame,
    identifier_snapshot_id: str | None,
    started_at: str | None,
    completed_at: str | None,
    warnings: tuple[str, ...],
    identifier_snapshot_checksum: str | None = None,
    identifier_snapshot_verified: bool = False,
) -> ExpressionNormalizationRunRecordV2:
    input_files = tuple(str(path) for path in (counts_path, metadata_path) if path)
    input_checksums = {
        str(path): _sha256_file(path) for path in (counts_path, metadata_path) if path.exists()
    }
    source_checksum = (
        _sha256_file(source_result_path)
        if source_result_path is not None and source_result_path.exists()
        else None
    )
    condition_counts = (
        metadata[config.condition_column].astype(str).value_counts().sort_index().to_dict()
        if config.condition_column in metadata.columns
        else {}
    )
    basis = {
        "input_checksums": input_checksums,
        "source_result_checksum": source_checksum,
        "organism": organism,
        "gene_id_namespace": config.gene_id_namespace,
        "identifier_snapshot_id": identifier_snapshot_id,
        "contrast_id": config.contrast_id,
        "normalization_method": config.normalization_method,
        "differential_method": config.differential_method,
        "backend": config.backend,
        "software": config.analysis_software,
        "software_version": config.analysis_software_version,
    }
    run_id = (
        "exprnorm-v2-"
        + hashlib.sha256(
            json.dumps(basis, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:20]
    )
    return ExpressionNormalizationRunRecordV2(
        schema_version=SCHEMA_VERSION,
        normalization_run_id=run_id,
        input_mode=support.input_mode,
        execution_support_level=support.execution_support_level,
        input_files=input_files,
        input_checksums=input_checksums,
        sample_metadata_file=str(metadata_path),
        sample_metadata_checksum=input_checksums.get(str(metadata_path)),
        source_result_checksum=source_checksum,
        organism=organism,
        gene_id_namespace=config.gene_id_namespace,
        identifier_snapshot_id=identifier_snapshot_id,
        sample_count=len(metadata),
        condition_count=len(condition_counts),
        replicate_counts={str(key): int(value) for key, value in condition_counts.items()},
        design_formula=config.design_formula,
        contrasts=(config.contrast_id,),
        covariates=(),
        batch_terms=(),
        normalization_method=config.normalization_method,
        normalization_parameters={},
        filtering_method=(
            "imported" if support.input_mode == "precomputed_de" else "backend_default"
        ),
        filtering_parameters={"min_baseline_count": config.min_baseline_count},
        differential_method=config.differential_method,
        differential_parameters={"effect_scale": config.effect_scale},
        shrinkage_method=config.shrinkage_method,
        shrinkage_status=config.shrinkage_status,
        multiple_testing_method=config.multiple_testing_method,
        software=config.analysis_software,
        software_version=config.analysis_software_version,
        adapter_name=config.backend or "unset",
        adapter_version="internal",
        execution_command_or_api="sirna_offtarget.expression",
        execution_environment={"python_package": "sirna_offtarget"},
        started_at=started_at,
        completed_at=completed_at,
        status="completed",
        output_checksums={},
        warnings=warnings,
        identifier_snapshot_checksum=identifier_snapshot_checksum,
        resolver_version="IdentifierResolverV2",
        identifier_ambiguity_policy=config.identifier_ambiguity_policy,
        identifier_snapshot_verified=identifier_snapshot_verified,
    )


def build_precomputed_gene_effect_records_v2(
    *,
    table: pd.DataFrame,
    config: ExpressionConfig,
    organism: str,
    contrast_id: str,
    normalization_run_id: str,
    source_checksum: str,
    resolutions: dict[str, IdentifierResolutionRecordV2],
) -> list[NormalizedGeneEffectRecordV2]:
    records: list[NormalizedGeneEffectRecordV2] = []
    for row_index, raw_row in enumerate(table.to_dict("records")):
        row = {str(key): value for key, value in raw_row.items()}
        original_gene_id = str(row.get(config.gene_column, ""))
        resolution = resolutions[original_gene_id]
        row_id = _source_row_identifier(row, row_index, config)
        reported = _optional_float(row.get(config.log2_fold_change_column))
        shrunken = _optional_float(row.get(config.shrunken_log2_fold_change_column))
        canonical, canonical_source = _canonical_effect(reported, shrunken)
        adjusted = _optional_float(row.get(config.adjusted_p_value_column))
        raw_p = _optional_float(row.get(config.p_value_column))
        imported_status = normalize_imported_status(
            tested=_row_get(row, config.tested_column),
            filter_status=_row_get(row, config.filter_status_column),
            low_count=_row_get(row, config.low_count_column),
            model_status=_row_get(row, config.model_status_column),
        )
        tested_status = imported_status.tested_status
        filter_status = imported_status.filter_status
        model_status = imported_status.model_status
        exclusion_reason = _optional_str(_row_get(row, config.exclusion_reason_column))
        warnings = _row_warnings(config, row, shrunken) + imported_status.warnings
        canonical_gene = resolution.canonical_gene_ids[0] if resolution.canonical_gene_ids else None
        record_id = _record_id(
            source_checksum,
            row_id,
            contrast_id,
            canonical_gene or original_gene_id,
            normalization_run_id,
        )
        records.append(
            NormalizedGeneEffectRecordV2(
                schema_version=SCHEMA_VERSION,
                record_id=record_id,
                original_gene_id=original_gene_id,
                original_gene_namespace=resolution.input_namespace,
                canonical_gene_id=canonical_gene,
                approved_symbol=resolution.approved_symbol,
                identifier_resolution_id=resolution.resolution_id,
                identifier_mapping_confidence=resolution.mapping_confidence,
                identifier_ambiguity_status=resolution.ambiguity_status,
                identifier_organism_match=resolution.organism_match,
                organism=organism,
                contrast_id=contrast_id,
                normalization_run_id=normalization_run_id,
                input_mode="precomputed_de",
                input_value_scale=config.value_scale,
                normalization_method=config.normalization_method,
                differential_method=config.differential_method,
                effect_scale=config.effect_scale,
                raw_effect_estimate=reported,
                reported_log2_fold_change=reported,
                shrunken_log2_fold_change=shrunken,
                canonical_log2_fold_change=canonical,
                canonical_effect_source=canonical_source,
                standard_error=_optional_float(row.get(config.standard_error_column)),
                confidence_interval_lower=_optional_float(
                    _row_get(row, config.confidence_interval_lower_column)
                ),
                confidence_interval_upper=_optional_float(
                    _row_get(row, config.confidence_interval_upper_column)
                ),
                test_statistic=_optional_float(_row_get(row, config.test_statistic_column)),
                raw_p_value=raw_p,
                adjusted_p_value=adjusted,
                adjusted_pvalue_status=_adjusted_pvalue_status(
                    adjusted, filter_status, model_status
                ),
                multiple_testing_method=config.multiple_testing_method,
                tested_status=tested_status,
                filter_status=filter_status,
                low_count_status=imported_status.low_count_status,
                model_status=model_status,
                exclusion_reason=exclusion_reason or resolution.exclusion_reason,
                numerical_direction=_numerical_direction(canonical, tested_status, model_status),
                statistical_support_status=_statistical_support(
                    adjusted, tested_status, filter_status, model_status, config.padj_threshold
                ),
                biological_threshold_status=_biological_threshold(
                    canonical, config.absolute_log2_fold_change
                ),
                direction_basis="canonical_log2_fold_change",
                control_abundance_summary=_optional_float(
                    _row_get(row, config.control_abundance_column)
                ),
                treatment_abundance_summary=_optional_float(
                    _row_get(row, config.treatment_abundance_column)
                ),
                mean_abundance_summary=_optional_float(row.get(config.base_mean_column)),
                replicate_count_control=None,
                replicate_count_treatment=None,
                design_formula=config.design_formula,
                covariates=(),
                batch_terms=(),
                analysis_software=config.analysis_software,
                analysis_software_version=config.analysis_software_version,
                provenance_record_ids=tuple(resolution.mapping_record_ids),
                source_row_identifier=row_id,
                warnings=warnings + tuple(resolution.warnings),
            )
        )
    return records


def build_legacy_gene_effect_records_v2(
    *,
    results: dict[str, ExpressionResult],
    config: ExpressionConfig,
    organism: str,
    contrast_id: str,
    normalization_run_id: str,
    source_checksum: str,
    resolutions: dict[str, IdentifierResolutionRecordV2],
) -> list[NormalizedGeneEffectRecordV2]:
    records: list[NormalizedGeneEffectRecordV2] = []
    for gene in sorted(results):
        result = results[gene]
        resolution = resolutions[gene]
        canonical_gene = resolution.canonical_gene_ids[0] if resolution.canonical_gene_ids else None
        canonical = (
            result.shrunken_log2_fold_change
            if result.shrinkage_status not in {"unavailable", "unspecified"}
            else result.log2_fold_change
        )
        source = (
            "backend_shrunken_log2fc"
            if result.shrinkage_status not in {"unavailable", "unspecified"}
            else "reported_unshrunken_log2fc"
        )
        row_id = f"legacy:{gene}"
        records.append(
            NormalizedGeneEffectRecordV2(
                schema_version=SCHEMA_VERSION,
                record_id=_record_id(
                    source_checksum,
                    row_id,
                    contrast_id,
                    canonical_gene or gene,
                    normalization_run_id,
                ),
                original_gene_id=gene,
                original_gene_namespace=resolution.input_namespace,
                canonical_gene_id=canonical_gene,
                approved_symbol=resolution.approved_symbol,
                identifier_resolution_id=resolution.resolution_id,
                identifier_mapping_confidence=resolution.mapping_confidence,
                identifier_ambiguity_status=resolution.ambiguity_status,
                identifier_organism_match=resolution.organism_match,
                organism=organism,
                contrast_id=contrast_id,
                normalization_run_id=normalization_run_id,
                input_mode=config.input_mode,
                input_value_scale=config.value_scale,
                normalization_method=config.normalization_method,
                differential_method=config.differential_method,
                effect_scale=config.effect_scale,
                raw_effect_estimate=result.log2_fold_change,
                reported_log2_fold_change=result.log2_fold_change,
                shrunken_log2_fold_change=result.shrunken_log2_fold_change,
                canonical_log2_fold_change=canonical,
                canonical_effect_source=source,
                standard_error=result.standard_error,
                confidence_interval_lower=None,
                confidence_interval_upper=None,
                test_statistic=None,
                raw_p_value=result.raw_p_value,
                adjusted_p_value=result.adjusted_p_value,
                adjusted_pvalue_status="adjusted_pvalue_available",
                multiple_testing_method=config.multiple_testing_method,
                tested_status="tested" if not result.low_count_flag else "filtered_low_count",
                filter_status="not_filtered" if not result.low_count_flag else "low_count_filter",
                low_count_status="low_count" if result.low_count_flag else "passes_count_filter",
                model_status="estimated",
                exclusion_reason=resolution.exclusion_reason,
                numerical_direction=_numerical_direction(canonical, "tested", "estimated"),
                statistical_support_status=_statistical_support(
                    result.adjusted_p_value,
                    "tested",
                    "not_filtered",
                    "estimated",
                    config.padj_threshold,
                ),
                biological_threshold_status=_biological_threshold(
                    canonical, config.absolute_log2_fold_change
                ),
                direction_basis="canonical_log2_fold_change",
                control_abundance_summary=result.normalized_control_expression,
                treatment_abundance_summary=result.normalized_treated_expression,
                mean_abundance_summary=result.baseline_expression,
                replicate_count_control=None,
                replicate_count_treatment=None,
                design_formula=config.design_formula,
                covariates=(),
                batch_terms=(),
                analysis_software=result.backend_name,
                analysis_software_version=result.backend_version,
                provenance_record_ids=tuple(resolution.mapping_record_ids),
                source_row_identifier=row_id,
                warnings=tuple(result.p_value_status for _ in [0]) + tuple(resolution.warnings),
            )
        )
    return records


def records_as_dicts_v2(records: list[Any]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        numeric = float(str(value))
    except ValueError:
        return None
    return None if pd.isna(numeric) else numeric


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_data(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _row_get(row: dict[str, Any], column: str | None) -> object:
    return row.get(column) if column is not None else None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text and text.lower() != "nan" else None


def _status_from_column(row: dict[str, Any], column: str | None, default: str) -> str:
    if not column:
        return default
    return _optional_str(row.get(column)) or "imported_missing"


def _source_row_identifier(row: dict[str, Any], row_index: int, config: ExpressionConfig) -> str:
    configured = (
        _optional_str(row.get(config.source_row_id_column))
        if config.source_row_id_column is not None
        else None
    )
    return configured or f"row:{row_index}:{row.get(config.gene_column, '')}"


def _canonical_effect(
    reported: float | None,
    shrunken: float | None,
) -> tuple[float | None, str]:
    if shrunken is not None:
        return shrunken, "imported_shrunken_log2fc"
    if reported is not None:
        return reported, "reported_unshrunken_log2fc"
    return None, "unavailable"


def _adjusted_pvalue_status(adjusted: float | None, filter_status: str, model_status: str) -> str:
    if adjusted is not None:
        return "adjusted_pvalue_available"
    if filter_status in {"independent_filtered", "outlier_filtered"}:
        return filter_status
    if model_status in {"model_not_estimable", "model_failure"}:
        return model_status
    return "adjusted_pvalue_unavailable"


def _numerical_direction(effect: float | None, tested_status: str, model_status: str) -> str:
    if tested_status in {"untested", "not_tested", "filtered_low_count"}:
        return "untested"
    if model_status in {"model_not_estimable", "model_failure"}:
        return "not_estimable"
    if effect is None:
        return "uncertain"
    if effect < 0:
        return "decreased"
    if effect > 0:
        return "increased"
    return "exact_zero"


def _statistical_support(
    adjusted: float | None,
    tested_status: str,
    filter_status: str,
    model_status: str,
    threshold: float,
) -> str:
    if tested_status in {"untested", "not_tested", "filtered_low_count"}:
        return "not_tested"
    if model_status in {"model_not_estimable", "model_failure"}:
        return "indeterminate"
    if filter_status in {"unsupported"}:
        return "unsupported"
    if adjusted is None:
        return "adjusted_pvalue_unavailable"
    return "significant" if adjusted <= threshold else "not_significant"


def _biological_threshold(effect: float | None, threshold: float | None) -> str:
    if effect is None:
        return "indeterminate"
    if threshold is None:
        return "threshold_not_configured"
    if effect <= -threshold:
        return "exceeds_decrease_threshold"
    if effect >= threshold:
        return "exceeds_increase_threshold"
    return "below_effect_threshold"


def _record_id(
    source_checksum: str,
    source_row_identifier: str,
    contrast_id: str,
    gene_identity: str,
    normalization_run_id: str,
) -> str:
    basis = "|".join(
        [source_checksum, source_row_identifier, contrast_id, gene_identity, normalization_run_id]
    )
    return "expr-effect-v2-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


def _row_warnings(
    config: ExpressionConfig, row: dict[str, Any], shrunken: float | None
) -> tuple[str, ...]:
    warnings: list[str] = []
    if config.control_abundance_column is None or config.treatment_abundance_column is None:
        warnings.append("condition-specific abundance summaries absent; values not invented")
    if shrunken is None:
        warnings.append("shrunken log2FC unavailable; not copied from reported log2FC")
    return tuple(warnings)
