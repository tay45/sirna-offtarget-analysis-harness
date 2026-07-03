from __future__ import annotations

from dataclasses import dataclass
from math import isclose, log2
from typing import Any

from sirna_offtarget.expected_direct_effect.contracts import (
    ExpectedDirectEffectPolicyV1,
    GeneExpectedDirectEffectRecordV1,
    IntendedTargetKnockdownCalibrationRecordV1,
    UnresolvedExpectedDirectEffectRecordV1,
    stable_id,
)
from sirna_offtarget.expression.contracts_v2 import NormalizedGeneEffectRecordV2
from sirna_offtarget.transcript_targetability_ratio.contracts import (
    GeneTranscriptTargetabilityRatioRecordV1,
)


@dataclass(frozen=True)
class ExpectedDirectEffectComputation:
    calibration: IntendedTargetKnockdownCalibrationRecordV1
    gene_effects: list[GeneExpectedDirectEffectRecordV1]
    unresolved: list[UnresolvedExpectedDirectEffectRecordV1]
    summary: dict[str, Any]
    warnings: list[str]


def _expression_key(record: NormalizedGeneEffectRecordV2) -> tuple[str, ...]:
    return tuple(
        item
        for item in (record.canonical_gene_id, record.approved_symbol, record.original_gene_id)
        if item
    )


def _expression_by_gene(
    records: list[NormalizedGeneEffectRecordV2],
) -> dict[str, NormalizedGeneEffectRecordV2]:
    by_gene: dict[str, NormalizedGeneEffectRecordV2] = {}
    for record in records:
        for key in _expression_key(record):
            by_gene.setdefault(key, record)
    return by_gene


def _ratio_by_gene(
    records: list[GeneTranscriptTargetabilityRatioRecordV1],
) -> dict[str, GeneTranscriptTargetabilityRatioRecordV1]:
    return {record.canonical_gene_id: record for record in records}


def _is_zero(value: float, tolerance: float) -> bool:
    return abs(value) <= tolerance


def _normalize_boundary(value: float, tolerance: float) -> float:
    if isclose(value, 0.0, rel_tol=0.0, abs_tol=tolerance):
        return 0.0
    if isclose(value, 1.0, rel_tol=0.0, abs_tol=tolerance):
        return 1.0
    return value


def _build_calibration(
    *,
    intended_target_gene_id: str,
    expression_by_gene: dict[str, NormalizedGeneEffectRecordV2],
    ratio_by_gene: dict[str, GeneTranscriptTargetabilityRatioRecordV1],
    policy: ExpectedDirectEffectPolicyV1,
    source_expression_checksum: str | None,
    source_ratio_checksum: str | None,
) -> IntendedTargetKnockdownCalibrationRecordV1:
    tolerance = policy.numerical_tolerance
    expression = expression_by_gene.get(intended_target_gene_id)
    ratio = ratio_by_gene.get(intended_target_gene_id)
    warnings: list[str] = []
    status = "definitive"
    observed: float | None = None
    remaining: float | None = None
    raw: float | None = None
    accepted: float | None = None
    targetable_fraction: float | None = None

    if expression is None or expression.canonical_gene_id is None:
        status = "unavailable_missing_expression"
        warnings.append("missing_intended_target_expression")
    elif ratio is None:
        status = "unavailable_invalid_intended_target"
        warnings.append("intended_target_identifier_not_in_ratio_artifact")
    elif (
        ratio.ratio_status != "definitive"
        or ratio.n_total_eligible_transcripts <= 0
        or ratio.m_targetable_transcripts is None
        or ratio.ratio_m_over_n is None
        or ratio.ratio_m_over_n <= 0
    ):
        status = "unavailable_intended_target_ratio"
        warnings.append("intended_target_ratio_unavailable_or_zero")
        targetable_fraction = ratio.ratio_m_over_n
    elif expression.canonical_log2_fold_change is None:
        status = "unavailable_missing_expression"
        warnings.append("missing_intended_target_normalized_log2fc")
        targetable_fraction = ratio.ratio_m_over_n
    else:
        observed = expression.canonical_log2_fold_change
        targetable_fraction = ratio.ratio_m_over_n
        remaining = 2**observed
        if _is_zero(observed, tolerance):
            status = "definitive_zero_no_decrease"
            raw = 0.0
            accepted = 0.0
        elif observed > 0:
            status = "unavailable_not_decreased"
            warnings.append("intended_target_not_decreased")
        else:
            raw = (1.0 - remaining) / targetable_fraction
            normalized = _normalize_boundary(raw, tolerance)
            if normalized < -tolerance:
                status = "unavailable_inconsistent_calibration"
                warnings.append("calibration_below_model_bound")
            elif normalized > 1.0 + tolerance:
                status = "unavailable_inconsistent_calibration"
                warnings.append("calibration_exceeds_model_bound")
            else:
                accepted = min(max(normalized, 0.0), 1.0)
                status = "definitive"

    provenance = []
    if expression is not None:
        provenance.append(expression.record_id)
    if ratio is not None:
        provenance.append(ratio.ratio_record_id)
    return IntendedTargetKnockdownCalibrationRecordV1(
        calibration_record_id=stable_id(
            "intended-target-calibration", intended_target_gene_id, observed, targetable_fraction
        ),
        intended_target_gene_id=intended_target_gene_id,
        intended_target_expression_record_id=expression.record_id if expression else None,
        intended_target_ratio_record_id=ratio.ratio_record_id if ratio else None,
        intended_target_normalized_log2fc=observed,
        intended_target_N=ratio.n_total_eligible_transcripts if ratio else None,
        intended_target_M=ratio.m_targetable_transcripts if ratio else None,
        intended_targetable_fraction=targetable_fraction,
        intended_observed_remaining_fraction=remaining,
        raw_calibration_knockdown_fraction=raw,
        accepted_calibration_knockdown_fraction=accepted,
        numerical_tolerance=tolerance,
        status=status,  # type: ignore[arg-type]
        warning_codes=tuple(warnings),
        provenance_record_ids=tuple(provenance),
        source_expression_checksum=source_expression_checksum,
        source_ratio_checksum=source_ratio_checksum,
    )


def _gene_effect_record(
    *,
    expression: NormalizedGeneEffectRecordV2 | None,
    ratio: GeneTranscriptTargetabilityRatioRecordV1,
    calibration: IntendedTargetKnockdownCalibrationRecordV1,
    policy: ExpectedDirectEffectPolicyV1,
) -> GeneExpectedDirectEffectRecordV1:
    observed = expression.canonical_log2_fold_change if expression else None
    accepted = calibration.accepted_calibration_knockdown_fraction
    warnings: list[str] = []
    expected_remaining: float | None = None
    expected_log2: float | None = None
    difference: float | None = None
    status = "definitive"
    reason: str | None = None
    targetable_fraction = ratio.ratio_m_over_n

    if expression is None or observed is None:
        status = "unavailable_missing_expression"
        reason = "missing_normalized_expression"
    elif ratio.ratio_status != "definitive" or targetable_fraction is None:
        status = "unavailable_ratio"
        reason = ratio.ratio_unavailable_reason or ratio.ratio_status
    elif accepted is None:
        status = "unavailable_calibration"
        reason = calibration.status
    else:
        expected_remaining = 1.0 - accepted * targetable_fraction
        if expected_remaining < -policy.numerical_tolerance:
            status = "unavailable_calibration"
            reason = "expected_remaining_fraction_below_zero"
            warnings.append(reason)
            expected_remaining = None
        else:
            expected_remaining = max(expected_remaining, 0.0)
            expected_log2 = float("-inf") if expected_remaining == 0 else log2(expected_remaining)
            difference = observed - expected_log2

    provenance = []
    if expression is not None:
        provenance.append(expression.record_id)
    provenance.append(ratio.ratio_record_id)
    provenance.append(calibration.calibration_record_id)
    return GeneExpectedDirectEffectRecordV1(
        expected_direct_effect_record_id=stable_id(
            "gene-expected-direct-effect",
            ratio.canonical_gene_id,
            expression.record_id if expression else None,
            ratio.ratio_record_id,
            calibration.calibration_record_id,
        ),
        canonical_gene_id=ratio.canonical_gene_id,
        approved_symbol=expression.approved_symbol if expression else None,
        source_expression_record_id=expression.record_id if expression else None,
        source_ratio_record_id=ratio.ratio_record_id,
        source_calibration_record_id=calibration.calibration_record_id,
        observed_normalized_log2fc=observed,
        n_total_eligible_transcripts=ratio.n_total_eligible_transcripts,
        m_targetable_transcripts=ratio.m_targetable_transcripts,
        targetable_fraction_m_over_n=targetable_fraction,
        ratio_status=ratio.ratio_status,
        intended_target_calibration_value=accepted,
        expected_remaining_fraction=expected_remaining,
        expected_direct_effect_log2fc=expected_log2,
        observed_vs_expected_log2_difference=difference,
        unresolved_residual_log2fc=difference,
        status=status,  # type: ignore[arg-type]
        unresolved_reason=reason,
        warning_codes=tuple(warnings),
        provenance_record_ids=tuple(provenance),
    )


def compute_expected_direct_effects(
    *,
    intended_target_gene_id: str,
    expression_records: list[NormalizedGeneEffectRecordV2],
    ratio_records: list[GeneTranscriptTargetabilityRatioRecordV1],
    policy: ExpectedDirectEffectPolicyV1 | None = None,
    source_expression_checksum: str | None = None,
    source_ratio_checksum: str | None = None,
) -> ExpectedDirectEffectComputation:
    active_policy = policy or ExpectedDirectEffectPolicyV1()
    expression_lookup = _expression_by_gene(expression_records)
    ratio_lookup = _ratio_by_gene(ratio_records)
    calibration = _build_calibration(
        intended_target_gene_id=intended_target_gene_id,
        expression_by_gene=expression_lookup,
        ratio_by_gene=ratio_lookup,
        policy=active_policy,
        source_expression_checksum=source_expression_checksum,
        source_ratio_checksum=source_ratio_checksum,
    )
    gene_effects: list[GeneExpectedDirectEffectRecordV1] = []
    unresolved: list[UnresolvedExpectedDirectEffectRecordV1] = []
    for gene_id in sorted(ratio_lookup):
        ratio = ratio_lookup[gene_id]
        expression = expression_lookup.get(gene_id)
        record = _gene_effect_record(
            expression=expression,
            ratio=ratio,
            calibration=calibration,
            policy=active_policy,
        )
        gene_effects.append(record)
        if record.status != "definitive":
            unresolved.append(
                UnresolvedExpectedDirectEffectRecordV1(
                    unresolved_record_id=stable_id(
                        "expected-direct-unresolved", gene_id, record.unresolved_reason
                    ),
                    canonical_gene_id=gene_id,
                    reason=record.unresolved_reason or record.status,
                    source_expression_record_id=record.source_expression_record_id,
                    source_ratio_record_id=record.source_ratio_record_id,
                    source_calibration_record_id=calibration.calibration_record_id,
                    preserved_upstream_status=record.ratio_status,
                    warnings=record.warning_codes,
                )
            )
    warnings = list(calibration.warning_codes)
    summary = {
        "genes_examined": len(gene_effects),
        "genes_with_definitive_expected_direct_effect": sum(
            record.status == "definitive" for record in gene_effects
        ),
        "genes_with_unavailable_expected_direct_effect": sum(
            record.status != "definitive" for record in gene_effects
        ),
        "genes_with_unresolved_residual": sum(
            record.unresolved_residual_log2fc is not None for record in gene_effects
        ),
        "genes_with_m_over_n_zero": sum(
            record.targetable_fraction_m_over_n == 0 for record in gene_effects
        ),
        "genes_with_m_over_n_one": sum(
            record.targetable_fraction_m_over_n == 1 for record in gene_effects
        ),
        "unresolved_records": len(unresolved),
        "calibration_status": calibration.status,
        "classification_performed": False,
        "pathway_evidence_used": False,
        "residual_interpretation": "unresolved_residual_only",
    }
    return ExpectedDirectEffectComputation(
        calibration=calibration,
        gene_effects=gene_effects,
        unresolved=unresolved,
        summary=summary,
        warnings=warnings,
    )
