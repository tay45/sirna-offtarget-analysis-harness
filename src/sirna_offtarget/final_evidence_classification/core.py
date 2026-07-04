from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Any

from sirna_offtarget.final_evidence_classification.contracts import (
    ClassificationConfidence,
    FinalEvidenceClassification,
    FinalEvidenceClassificationPolicyV1,
    FinalEvidenceClassificationUnresolvedRecordV1,
    GeneFinalEvidenceClassificationRecordV1,
    stable_id,
)
from sirna_offtarget.secondary_evidence_integration.contracts import (
    GeneSecondaryEvidenceIntegrationRecordV1,
    SecondaryEvidenceIntegrationUnresolvedRecordV1,
)


@dataclass(frozen=True)
class ClassificationDecision:
    classification: FinalEvidenceClassification
    confidence: ClassificationConfidence
    reason: str
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class FinalEvidenceClassificationComputation:
    gene_classifications: list[GeneFinalEvidenceClassificationRecordV1]
    unresolved: list[FinalEvidenceClassificationUnresolvedRecordV1]
    summary: dict[str, Any]
    warnings: list[str]


def _expected_available(component: str) -> bool:
    return component in {"expected_direct_effect_available", "expected_direct_effect_nonzero"}


def _expected_zero_or_unavailable(component: str) -> bool:
    return component in {"expected_direct_effect_zero", "expected_direct_effect_unavailable"}


def _targetability_definitive(record: GeneSecondaryEvidenceIntegrationRecordV1) -> bool:
    return record.direct_sequence_evidence_component == "definitive_targetable_fraction_present"


def _targetability_unresolved(record: GeneSecondaryEvidenceIntegrationRecordV1) -> bool:
    return record.direct_sequence_evidence_component in {
        "unresolved_targetability",
        "unavailable_targetability",
    }


def _residual_negligible(record: GeneSecondaryEvidenceIntegrationRecordV1) -> bool:
    return record.residual_evidence_component == "no_residual_to_integrate"


def _residual_weak_or_negligible(record: GeneSecondaryEvidenceIntegrationRecordV1) -> bool:
    return record.residual_evidence_component in {
        "no_residual_to_integrate",
        "weak_residual_evidence",
    }


def _residual_moderate_or_strong(record: GeneSecondaryEvidenceIntegrationRecordV1) -> bool:
    return record.residual_evidence_component in {
        "moderate_residual_evidence",
        "strong_residual_evidence",
    }


def _pathway_moderate_or_strong(record: GeneSecondaryEvidenceIntegrationRecordV1) -> bool:
    return record.pathway_support_component in {
        "residual_with_moderate_pathway_support",
        "residual_with_strong_pathway_support",
    }


def _has_expression_effect(
    record: GeneSecondaryEvidenceIntegrationRecordV1,
    policy: FinalEvidenceClassificationPolicyV1,
) -> bool:
    return not isclose(
        record.observed_normalized_log2fc,
        0.0,
        rel_tol=0.0,
        abs_tol=policy.numerical_tolerance,
    )


def _any_unresolved_component(record: GeneSecondaryEvidenceIntegrationRecordV1) -> bool:
    return (
        record.direct_sequence_evidence_component
        in {"unresolved_targetability", "unavailable_targetability"}
        or record.expected_direct_effect_component == "expected_direct_effect_unavailable"
        or record.residual_evidence_component == "unresolved_residual_evidence"
        or record.pathway_support_component
        in {"unresolved_missing_pathway_evidence", "unresolved_upstream_expected_effect"}
        or record.evidence_readiness_status
        in {
            "ready_with_unresolved_pathway_context",
            "ready_with_unresolved_targetability",
            "insufficient_expected_effect_evidence",
            "insufficient_residual_evidence",
            "unresolved_upstream_residual_attribution",
        }
    )


def _confidence(
    record: GeneSecondaryEvidenceIntegrationRecordV1,
    classification: FinalEvidenceClassification,
) -> ClassificationConfidence:
    if classification == "unresolved":
        return "unresolved"
    if classification == "no_evidence_for_effect":
        return "low" if _any_unresolved_component(record) else "moderate"
    if _any_unresolved_component(record):
        return "moderate"
    if classification == "direct_compatible":
        if (
            _expected_available(record.expected_direct_effect_component)
            and _residual_negligible(record)
            and _targetability_definitive(record)
        ):
            return "high"
        return "moderate"
    if classification == "secondary_supported":
        if (
            record.residual_evidence_component == "strong_residual_evidence"
            and record.pathway_support_component == "residual_with_strong_pathway_support"
        ):
            return "high"
        return "moderate"
    if classification == "mixed_supported":
        if (
            _targetability_definitive(record)
            and record.residual_evidence_component == "strong_residual_evidence"
            and record.pathway_support_component == "residual_with_strong_pathway_support"
        ):
            return "high"
        return "moderate"
    return "unresolved"


def _classify(
    record: GeneSecondaryEvidenceIntegrationRecordV1,
    policy: FinalEvidenceClassificationPolicyV1,
) -> ClassificationDecision:
    if record.evidence_readiness_status == "unresolved_upstream_residual_attribution":
        return ClassificationDecision(
            "unresolved",
            "unresolved",
            "unresolved_upstream_secondary_evidence_integration",
        )
    if record.evidence_readiness_status == "insufficient_expected_effect_evidence":
        return ClassificationDecision("unresolved", "unresolved", "insufficient_expected_effect")
    if _targetability_unresolved(record):
        if (
            _residual_negligible(record)
            and _expected_zero_or_unavailable(record.expected_direct_effect_component)
            and not _has_expression_effect(record, policy)
        ):
            return ClassificationDecision(
                "no_evidence_for_effect",
                _confidence(record, "no_evidence_for_effect"),
                "unresolved_targetability_with_negligible_no_effect_evidence",
            )
        return ClassificationDecision("unresolved", "unresolved", "unresolved_targetability")
    if _residual_negligible(record) and _expected_zero_or_unavailable(
        record.expected_direct_effect_component
    ):
        return ClassificationDecision(
            "no_evidence_for_effect",
            _confidence(record, "no_evidence_for_effect"),
            "negligible_residual_and_no_expected_direct_effect",
        )
    if (
        _targetability_definitive(record)
        and _residual_moderate_or_strong(record)
        and _pathway_moderate_or_strong(record)
    ):
        return ClassificationDecision(
            "mixed_supported",
            _confidence(record, "mixed_supported"),
            "direct_compatible_evidence_with_residual_pathway_support",
        )
    if (
        _residual_moderate_or_strong(record)
        and _pathway_moderate_or_strong(record)
        and record.direct_sequence_evidence_component == "no_cleavage_compatible_targetability"
    ):
        return ClassificationDecision(
            "secondary_supported",
            _confidence(record, "secondary_supported"),
            "residual_pathway_support_without_cleavage_compatible_targetability",
        )
    if (
        _targetability_definitive(record)
        and _expected_available(record.expected_direct_effect_component)
        and _residual_weak_or_negligible(record)
        and record.residual_support_status
        in {"no_residual_to_attribute", "residual_without_pathway_support"}
    ):
        return ClassificationDecision(
            "direct_compatible",
            _confidence(record, "direct_compatible"),
            "targetability_and_expected_effect_consistent_with_observed_change",
        )
    if (
        not _residual_negligible(record)
        and record.pathway_support_component == "unresolved_missing_pathway_evidence"
    ):
        return ClassificationDecision("unresolved", "unresolved", "unresolved_pathway_context")
    if (
        not _residual_negligible(record)
        and record.pathway_support_component == "residual_without_pathway_support"
    ):
        return ClassificationDecision(
            "unresolved",
            "unresolved",
            "residual_without_pathway_support",
        )
    if (
        _has_expression_effect(record, policy)
        and _targetability_unresolved(record)
        and record.pathway_support_component == "unresolved_missing_pathway_evidence"
    ):
        return ClassificationDecision("unresolved", "unresolved", "unresolved_evidence_context")
    return ClassificationDecision("unresolved", "unresolved", "conservative_unresolved")


def _unresolved_from_upstream(
    record: SecondaryEvidenceIntegrationUnresolvedRecordV1,
) -> FinalEvidenceClassificationUnresolvedRecordV1:
    return FinalEvidenceClassificationUnresolvedRecordV1(
        unresolved_record_id=stable_id(
            "final-evidence-classification-unresolved",
            record.gene_id,
            record.unresolved_record_id,
            record.reason,
        ),
        gene_id=record.gene_id,
        reason="unresolved_upstream_secondary_evidence_integration",
        source_secondary_evidence_integration_record_id=record.unresolved_record_id,
        preserved_upstream_status=record.reason,
        warning_codes=record.warning_codes,
    )


def compute_final_evidence_classification(
    *,
    secondary_evidence_records: list[GeneSecondaryEvidenceIntegrationRecordV1],
    secondary_unresolved_records: list[SecondaryEvidenceIntegrationUnresolvedRecordV1]
    | None = None,
    policy: FinalEvidenceClassificationPolicyV1 | None = None,
    source_secondary_evidence_integration_checksum: str | None = None,
) -> FinalEvidenceClassificationComputation:
    active_policy = policy or FinalEvidenceClassificationPolicyV1()
    gene_classifications: list[GeneFinalEvidenceClassificationRecordV1] = []
    unresolved = [
        _unresolved_from_upstream(record)
        for record in sorted(
            secondary_unresolved_records or [],
            key=lambda item: (item.gene_id, item.unresolved_record_id),
        )
    ]
    warnings: list[str] = []

    for record in sorted(
        secondary_evidence_records,
        key=lambda item: (item.gene_id, item.integration_record_id),
    ):
        decision = _classify(record, active_policy)
        if decision.classification == "unresolved":
            unresolved.append(
                FinalEvidenceClassificationUnresolvedRecordV1(
                    unresolved_record_id=stable_id(
                        "final-evidence-classification-unresolved",
                        record.gene_id,
                        record.integration_record_id,
                        decision.reason,
                    ),
                    gene_id=record.gene_id,
                    reason=decision.reason,
                    source_secondary_evidence_integration_record_id=record.integration_record_id,
                    preserved_upstream_status=record.evidence_readiness_status,
                    warning_codes=record.warning_codes,
                )
            )
        gene_classifications.append(
            GeneFinalEvidenceClassificationRecordV1(
                classification_record_id=stable_id(
                    "gene-final-evidence-classification",
                    record.gene_id,
                    record.integration_record_id,
                    decision.classification,
                    decision.confidence,
                    decision.reason,
                ),
                gene_id=record.gene_id,
                secondary_evidence_integration_record_id=record.integration_record_id,
                final_evidence_classification=decision.classification,
                classification_confidence=decision.confidence,
                classification_reason=decision.reason,
                observed_normalized_log2fc=record.observed_normalized_log2fc,
                expected_direct_effect_log2fc=record.expected_direct_effect_log2fc,
                observed_vs_expected_log2_difference=record.observed_vs_expected_log2_difference,
                unresolved_residual_log2fc=record.unresolved_residual_log2fc,
                residual_direction=record.residual_direction,
                residual_magnitude_status=record.residual_magnitude_status,
                residual_support_status=record.residual_support_status,
                direct_sequence_evidence_component=record.direct_sequence_evidence_component,
                expected_direct_effect_component=record.expected_direct_effect_component,
                residual_evidence_component=record.residual_evidence_component,
                pathway_support_component=record.pathway_support_component,
                evidence_readiness_status=record.evidence_readiness_status,
                targetability_fields_preserved=dict(record.targetability_fields_preserved),
                calibration_fields_preserved=dict(record.calibration_fields_preserved),
                pathway_support_summary=dict(record.pathway_support_summary),
                upstream_warning_codes=record.warning_codes,
                classification_warning_codes=decision.warning_codes,
                provenance_record_ids=(record.integration_record_id, *record.provenance_record_ids),
                source_secondary_evidence_integration_checksum=(
                    source_secondary_evidence_integration_checksum
                ),
            )
        )

    counts = {
        label: sum(item.final_evidence_classification == label for item in gene_classifications)
        for label in (
            "direct_compatible",
            "secondary_supported",
            "mixed_supported",
            "no_evidence_for_effect",
            "unresolved",
        )
    }
    confidence_counts = {
        f"confidence_{label}": sum(
            item.classification_confidence == label for item in gene_classifications
        )
        for label in ("low", "moderate", "high", "unresolved")
    }
    summary = {
        "genes_examined": len(secondary_evidence_records) + len(secondary_unresolved_records or []),
        "genes_with_final_evidence_classification": len(gene_classifications),
        "unresolved_records": len(unresolved),
        "classification_labels_are_evidence_based": True,
        "definitive_biological_claims_made": False,
        "clinical_toxicological_or_regulatory_claims_made": False,
        "missing_evidence_as_negative": False,
        **counts,
        **confidence_counts,
    }
    if counts["unresolved"]:
        warnings.append("some_genes_remain_unresolved_under_conservative_policy")
    return FinalEvidenceClassificationComputation(
        gene_classifications=gene_classifications,
        unresolved=unresolved,
        summary=summary,
        warnings=warnings,
    )
