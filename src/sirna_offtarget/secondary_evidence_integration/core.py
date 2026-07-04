from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Any

from sirna_offtarget.residual_attribution.contracts import (
    GeneResidualAttributionEvidenceRecordV1,
    ResidualAttributionUnresolvedRecordV1,
)
from sirna_offtarget.secondary_evidence_integration.contracts import (
    DirectSequenceEvidenceComponent,
    EvidenceReadinessStatus,
    ExpectedDirectEffectComponent,
    GeneSecondaryEvidenceIntegrationRecordV1,
    PathwaySupportComponent,
    ResidualEvidenceComponent,
    SecondaryEvidenceIntegrationPolicyV1,
    SecondaryEvidenceIntegrationUnresolvedRecordV1,
    stable_id,
)


@dataclass(frozen=True)
class SecondaryEvidenceIntegrationComputation:
    gene_evidence: list[GeneSecondaryEvidenceIntegrationRecordV1]
    unresolved: list[SecondaryEvidenceIntegrationUnresolvedRecordV1]
    summary: dict[str, Any]
    warnings: list[str]


def _direct_sequence_component(
    targetability_fields: dict[str, object],
) -> DirectSequenceEvidenceComponent:
    ratio_status = targetability_fields.get("ratio_status")
    m_value = targetability_fields.get("m_targetable_transcripts")
    fraction = targetability_fields.get("targetable_fraction_m_over_n")
    n_value = targetability_fields.get("n_total_eligible_transcripts")

    if ratio_status is None:
        return "unavailable_targetability"
    if ratio_status != "definitive":
        return "unresolved_targetability"
    if n_value is None:
        return "unresolved_targetability"
    if isinstance(m_value, int) and m_value > 0:
        return "definitive_targetable_fraction_present"
    if isinstance(fraction, float) and fraction > 0.0:
        return "definitive_targetable_fraction_present"
    return "no_cleavage_compatible_targetability"


def _expected_direct_component(
    expected_direct_effect_log2fc: float | None,
    policy: SecondaryEvidenceIntegrationPolicyV1,
) -> ExpectedDirectEffectComponent:
    if expected_direct_effect_log2fc is None:
        return "expected_direct_effect_unavailable"
    if isclose(expected_direct_effect_log2fc, 0.0, rel_tol=0.0, abs_tol=policy.numerical_tolerance):
        return "expected_direct_effect_zero"
    return "expected_direct_effect_nonzero"


def _residual_component(
    residual_log2fc: float | None,
    residual_magnitude_status: str | None,
) -> ResidualEvidenceComponent:
    if residual_log2fc is None or residual_magnitude_status is None:
        return "unresolved_residual_evidence"
    if residual_magnitude_status == "negligible_residual":
        return "no_residual_to_integrate"
    if residual_magnitude_status == "weak_residual":
        return "weak_residual_evidence"
    if residual_magnitude_status == "moderate_residual":
        return "moderate_residual_evidence"
    if residual_magnitude_status == "strong_residual":
        return "strong_residual_evidence"
    return "unresolved_residual_evidence"


def _pathway_component(residual_support_status: str) -> PathwaySupportComponent:
    allowed = {
        "no_residual_to_attribute",
        "residual_without_pathway_support",
        "residual_with_weak_pathway_support",
        "residual_with_moderate_pathway_support",
        "residual_with_strong_pathway_support",
        "unresolved_missing_pathway_evidence",
        "unresolved_upstream_expected_effect",
    }
    if residual_support_status in allowed:
        return residual_support_status  # type: ignore[return-value]
    return "unresolved_upstream_expected_effect"


def _readiness(
    *,
    expected_component: ExpectedDirectEffectComponent,
    direct_sequence_component: DirectSequenceEvidenceComponent,
    residual_component: ResidualEvidenceComponent,
    pathway_component: PathwaySupportComponent,
) -> EvidenceReadinessStatus:
    if pathway_component == "unresolved_upstream_expected_effect":
        return "unresolved_upstream_residual_attribution"
    if expected_component == "expected_direct_effect_unavailable":
        return "insufficient_expected_effect_evidence"
    if direct_sequence_component in {"unresolved_targetability", "unavailable_targetability"}:
        return "ready_with_unresolved_targetability"
    if residual_component == "unresolved_residual_evidence":
        return "insufficient_residual_evidence"
    if (
        residual_component != "no_residual_to_integrate"
        and pathway_component == "unresolved_missing_pathway_evidence"
    ):
        return "ready_with_unresolved_pathway_context"
    return "ready_for_final_classification"


def _calibration_fields(record: GeneResidualAttributionEvidenceRecordV1) -> dict[str, object]:
    return {
        "intended_target_calibration_value": record.intended_target_calibration_value,
    }


def _unresolved_from_upstream(
    record: ResidualAttributionUnresolvedRecordV1,
) -> SecondaryEvidenceIntegrationUnresolvedRecordV1:
    return SecondaryEvidenceIntegrationUnresolvedRecordV1(
        unresolved_record_id=stable_id(
            "secondary-evidence-integration-unresolved",
            record.gene_id,
            record.unresolved_record_id,
            record.reason,
        ),
        gene_id=record.gene_id,
        reason="unresolved_upstream_residual_attribution",
        source_residual_attribution_record_id=record.unresolved_record_id,
        preserved_upstream_status=record.reason,
        warning_codes=record.warning_codes,
    )


def compute_secondary_evidence_integration(
    *,
    residual_attribution_records: list[GeneResidualAttributionEvidenceRecordV1],
    residual_unresolved_records: list[ResidualAttributionUnresolvedRecordV1] | None = None,
    policy: SecondaryEvidenceIntegrationPolicyV1 | None = None,
    source_residual_attribution_checksum: str | None = None,
) -> SecondaryEvidenceIntegrationComputation:
    active_policy = policy or SecondaryEvidenceIntegrationPolicyV1()
    evidence: list[GeneSecondaryEvidenceIntegrationRecordV1] = []
    unresolved = [
        _unresolved_from_upstream(record)
        for record in sorted(
            residual_unresolved_records or [],
            key=lambda item: (item.gene_id, item.unresolved_record_id),
        )
    ]
    warnings: list[str] = []

    for record in sorted(
        residual_attribution_records,
        key=lambda item: (item.gene_id, item.residual_attribution_record_id),
    ):
        direct_sequence = _direct_sequence_component(record.targetability_fields_preserved)
        expected_direct = _expected_direct_component(
            record.expected_direct_effect_log2fc,
            active_policy,
        )
        residual = _residual_component(
            record.unresolved_residual_log2fc,
            record.residual_magnitude_status,
        )
        pathway = _pathway_component(record.residual_support_status)
        readiness = _readiness(
            expected_component=expected_direct,
            direct_sequence_component=direct_sequence,
            residual_component=residual,
            pathway_component=pathway,
        )
        if readiness in {
            "ready_with_unresolved_pathway_context",
            "ready_with_unresolved_targetability",
            "insufficient_expected_effect_evidence",
            "insufficient_residual_evidence",
            "unresolved_upstream_residual_attribution",
        }:
            unresolved.append(
                SecondaryEvidenceIntegrationUnresolvedRecordV1(
                    unresolved_record_id=stable_id(
                        "secondary-evidence-integration-unresolved",
                        record.gene_id,
                        record.residual_attribution_record_id,
                        readiness,
                    ),
                    gene_id=record.gene_id,
                    reason=readiness,
                    source_residual_attribution_record_id=record.residual_attribution_record_id,
                    preserved_upstream_status=record.residual_support_status,
                    warning_codes=record.warning_codes,
                )
            )

        evidence.append(
            GeneSecondaryEvidenceIntegrationRecordV1(
                integration_record_id=stable_id(
                    "gene-secondary-evidence-integration",
                    record.gene_id,
                    record.residual_attribution_record_id,
                    direct_sequence,
                    expected_direct,
                    residual,
                    pathway,
                    readiness,
                ),
                gene_id=record.gene_id,
                residual_attribution_record_id=record.residual_attribution_record_id,
                observed_normalized_log2fc=record.observed_normalized_log2fc,
                expected_direct_effect_log2fc=record.expected_direct_effect_log2fc,
                observed_vs_expected_log2_difference=record.observed_vs_expected_log2_difference,
                unresolved_residual_log2fc=record.unresolved_residual_log2fc,
                residual_direction=record.residual_direction,
                residual_magnitude_status=record.residual_magnitude_status,
                residual_support_status=record.residual_support_status,
                direct_sequence_evidence_component=direct_sequence,
                expected_direct_effect_component=expected_direct,
                residual_evidence_component=residual,
                pathway_support_component=pathway,
                evidence_readiness_status=readiness,
                targetability_fields_preserved=dict(record.targetability_fields_preserved),
                calibration_fields_preserved=_calibration_fields(record),
                pathway_support_summary=dict(record.pathway_support_summary),
                warning_codes=record.warning_codes,
                provenance_record_ids=(
                    record.residual_attribution_record_id,
                    *record.provenance_record_ids,
                ),
                source_residual_attribution_checksum=source_residual_attribution_checksum,
            )
        )

    readiness_counts = {
        status: sum(item.evidence_readiness_status == status for item in evidence)
        for status in (
            "ready_for_final_classification",
            "ready_with_unresolved_pathway_context",
            "ready_with_unresolved_targetability",
            "insufficient_expected_effect_evidence",
            "insufficient_residual_evidence",
            "unresolved_upstream_residual_attribution",
        )
    }
    summary = {
        "genes_examined": len(residual_attribution_records)
        + len(residual_unresolved_records or []),
        "genes_with_secondary_evidence_integration": len(evidence),
        "unresolved_records": len(unresolved),
        "classification_performed": False,
        "classification_ready_evidence_only": True,
        "missing_pathway_evidence_interpretation": "unresolved_not_negative",
        **readiness_counts,
    }
    if any(
        item.evidence_readiness_status == "ready_with_unresolved_pathway_context"
        for item in evidence
    ):
        warnings.append("missing_pathway_evidence_preserved_as_unresolved_context")
    return SecondaryEvidenceIntegrationComputation(
        gene_evidence=evidence,
        unresolved=unresolved,
        summary=summary,
        warnings=warnings,
    )
