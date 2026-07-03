from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Any

from sirna_offtarget.expected_direct_effect.contracts import GeneExpectedDirectEffectRecordV1
from sirna_offtarget.residual_attribution.contracts import (
    GeneResidualAttributionEvidenceRecordV1,
    ResidualAttributionPolicyV1,
    ResidualAttributionUnresolvedRecordV1,
    ResidualDirection,
    ResidualMagnitudeStatus,
    ResidualSupportStatus,
    stable_id,
)


@dataclass(frozen=True)
class PathwaySupportEvidence:
    record_id: str
    evidence_kind: str
    support_strength: str = "supporting_context"
    summary: dict[str, object] | None = None


@dataclass(frozen=True)
class ResidualAttributionComputation:
    gene_evidence: list[GeneResidualAttributionEvidenceRecordV1]
    unresolved: list[ResidualAttributionUnresolvedRecordV1]
    summary: dict[str, Any]
    warnings: list[str]


def _direction(value: float, tolerance: float) -> ResidualDirection:
    if isclose(value, 0.0, rel_tol=0.0, abs_tol=tolerance):
        return "matches_expected_direct_effect"
    if value < 0:
        return "more_decreased_than_expected"
    return "less_decreased_or_increased_than_expected"


def _magnitude(value: float, policy: ResidualAttributionPolicyV1) -> ResidualMagnitudeStatus:
    residual_abs = abs(value)
    if residual_abs <= policy.negligible_residual_abs_log2_threshold:
        return "negligible_residual"
    if residual_abs < policy.moderate_residual_abs_log2_threshold:
        return "weak_residual"
    if residual_abs < policy.strong_residual_abs_log2_threshold:
        return "moderate_residual"
    return "strong_residual"


def _support_status(
    *,
    magnitude: ResidualMagnitudeStatus,
    pathway_available: bool,
    support_count: int,
    policy: ResidualAttributionPolicyV1,
) -> ResidualSupportStatus:
    if magnitude == "negligible_residual":
        return "no_residual_to_attribute"
    if not pathway_available:
        return "unresolved_missing_pathway_evidence"
    if support_count <= 0:
        return "residual_without_pathway_support"
    if support_count >= policy.strong_pathway_support_min_count:
        return "residual_with_strong_pathway_support"
    if support_count >= policy.moderate_pathway_support_min_count:
        return "residual_with_moderate_pathway_support"
    return "residual_with_weak_pathway_support"


def _support_summary(items: list[PathwaySupportEvidence], *, available: bool) -> dict[str, object]:
    kinds: dict[str, int] = {}
    for item in items:
        kinds[item.evidence_kind] = kinds.get(item.evidence_kind, 0) + 1
    return {
        "pathway_evidence_available": available,
        "support_count": len(items),
        "support_by_kind": kinds,
        "missing_pathway_evidence_interpretation": "unresolved_not_negative",
        "supporting_context_only": True,
    }


def _targetability_fields(record: GeneExpectedDirectEffectRecordV1) -> dict[str, object]:
    return {
        "source_ratio_record_id": record.source_ratio_record_id,
        "n_total_eligible_transcripts": record.n_total_eligible_transcripts,
        "m_targetable_transcripts": record.m_targetable_transcripts,
        "targetable_fraction_m_over_n": record.targetable_fraction_m_over_n,
        "ratio_status": record.ratio_status,
    }


def _unresolved(
    record: GeneExpectedDirectEffectRecordV1,
    reason: ResidualSupportStatus,
) -> ResidualAttributionUnresolvedRecordV1:
    return ResidualAttributionUnresolvedRecordV1(
        unresolved_record_id=stable_id(
            "residual-attribution-unresolved",
            record.canonical_gene_id,
            record.expected_direct_effect_record_id,
            reason,
        ),
        gene_id=record.canonical_gene_id,
        reason=reason,
        source_expected_direct_effect_record_id=record.expected_direct_effect_record_id,
        preserved_upstream_status=record.status,
        warning_codes=record.warning_codes,
    )


def compute_residual_attribution(
    *,
    expected_direct_effect_records: list[GeneExpectedDirectEffectRecordV1],
    pathway_support_by_gene: dict[str, list[PathwaySupportEvidence]] | None = None,
    pathway_evidence_available: bool = False,
    policy: ResidualAttributionPolicyV1 | None = None,
    source_expected_direct_effect_checksum: str | None = None,
    source_pathway_evidence_checksum: str | None = None,
) -> ResidualAttributionComputation:
    active_policy = policy or ResidualAttributionPolicyV1()
    support_lookup = pathway_support_by_gene or {}
    evidence: list[GeneResidualAttributionEvidenceRecordV1] = []
    unresolved: list[ResidualAttributionUnresolvedRecordV1] = []
    warnings: list[str] = []

    for record in sorted(
        expected_direct_effect_records,
        key=lambda item: (item.canonical_gene_id, item.expected_direct_effect_record_id),
    ):
        if record.status != "definitive" or record.unresolved_residual_log2fc is None:
            unresolved.append(_unresolved(record, "unresolved_upstream_expected_effect"))
            continue
        if (
            record.observed_normalized_log2fc is None
            or record.expected_direct_effect_log2fc is None
            or record.observed_vs_expected_log2_difference is None
        ):
            unresolved.append(_unresolved(record, "unresolved_upstream_expected_effect"))
            continue

        residual = record.unresolved_residual_log2fc
        residual_abs = abs(residual)
        magnitude = _magnitude(residual, active_policy)
        supports = support_lookup.get(record.canonical_gene_id, [])
        support_status = _support_status(
            magnitude=magnitude,
            pathway_available=pathway_evidence_available,
            support_count=len(supports),
            policy=active_policy,
        )
        if support_status == "unresolved_missing_pathway_evidence":
            unresolved.append(_unresolved(record, support_status))
        evidence.append(
            GeneResidualAttributionEvidenceRecordV1(
                residual_attribution_record_id=stable_id(
                    "gene-residual-attribution",
                    record.canonical_gene_id,
                    record.expected_direct_effect_record_id,
                    residual,
                    tuple(item.record_id for item in supports),
                ),
                gene_id=record.canonical_gene_id,
                expected_direct_effect_record_id=record.expected_direct_effect_record_id,
                observed_normalized_log2fc=record.observed_normalized_log2fc,
                expected_direct_effect_log2fc=record.expected_direct_effect_log2fc,
                observed_vs_expected_log2_difference=(record.observed_vs_expected_log2_difference),
                unresolved_residual_log2fc=residual,
                residual_abs_log2=residual_abs,
                residual_direction=_direction(residual, active_policy.numerical_tolerance),
                residual_magnitude_status=magnitude,
                pathway_evidence_record_ids=tuple(item.record_id for item in supports),
                pathway_support_count=len(supports),
                pathway_support_summary=_support_summary(
                    supports, available=pathway_evidence_available
                ),
                residual_support_status=support_status,
                targetability_fields_preserved=_targetability_fields(record),
                intended_target_calibration_value=record.intended_target_calibration_value,
                warning_codes=record.warning_codes,
                provenance_record_ids=(
                    record.expected_direct_effect_record_id,
                    *record.provenance_record_ids,
                    *(item.record_id for item in supports),
                ),
                source_expected_direct_effect_checksum=source_expected_direct_effect_checksum,
                source_pathway_evidence_checksum=source_pathway_evidence_checksum,
            )
        )

    support_counts = {
        status: sum(item.residual_support_status == status for item in evidence)
        for status in (
            "no_residual_to_attribute",
            "residual_without_pathway_support",
            "residual_with_weak_pathway_support",
            "residual_with_moderate_pathway_support",
            "residual_with_strong_pathway_support",
            "unresolved_missing_pathway_evidence",
        )
    }
    summary = {
        "genes_examined": len(expected_direct_effect_records),
        "genes_with_residual_attribution_evidence": len(evidence),
        "unresolved_records": len(unresolved),
        "genes_with_unresolved_upstream_expected_effect": sum(
            item.reason == "unresolved_upstream_expected_effect" for item in unresolved
        ),
        "pathway_evidence_available": pathway_evidence_available,
        "classification_performed": False,
        "supporting_context_only": True,
        "direct_secondary_mixed_boundary": "classification_planned_not_performed",
        **support_counts,
    }
    if not pathway_evidence_available:
        warnings.append("missing_pathway_evidence_preserved_as_unresolved")
    return ResidualAttributionComputation(
        gene_evidence=evidence,
        unresolved=unresolved,
        summary=summary,
        warnings=warnings,
    )
