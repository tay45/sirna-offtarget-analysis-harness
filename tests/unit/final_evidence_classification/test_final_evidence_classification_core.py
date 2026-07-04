from __future__ import annotations

import pytest

from sirna_offtarget.final_evidence_classification.contracts import (
    CLASSIFICATION_INTERPRETATION_BOUNDARY,
    FinalEvidenceClassificationPolicyV1,
    GeneFinalEvidenceClassificationRecordV1,
)
from sirna_offtarget.final_evidence_classification.core import (
    compute_final_evidence_classification,
)
from sirna_offtarget.secondary_evidence_integration.contracts import (
    GeneSecondaryEvidenceIntegrationRecordV1,
    SecondaryEvidenceIntegrationUnresolvedRecordV1,
)


def integrated_record(
    gene: str = "GENE",
    *,
    direct_component: str = "definitive_targetable_fraction_present",
    expected_component: str = "expected_direct_effect_nonzero",
    residual_component: str = "no_residual_to_integrate",
    pathway_component: str = "no_residual_to_attribute",
    readiness: str = "ready_for_final_classification",
    observed_log2: float = -0.5,
    expected_log2: float | None = -0.5,
    residual_log2: float | None = 0.0,
    residual_magnitude: str | None = "negligible_residual",
    residual_support: str = "no_residual_to_attribute",
    m_value: int | None = 1,
    fraction: float | None = 1.0,
) -> GeneSecondaryEvidenceIntegrationRecordV1:
    return GeneSecondaryEvidenceIntegrationRecordV1(
        integration_record_id=f"sei-{gene}",
        gene_id=gene,
        residual_attribution_record_id=f"ra-{gene}",
        observed_normalized_log2fc=observed_log2,
        expected_direct_effect_log2fc=expected_log2,
        observed_vs_expected_log2_difference=residual_log2,
        unresolved_residual_log2fc=residual_log2,
        residual_direction="matches_expected_direct_effect",
        residual_magnitude_status=residual_magnitude,
        residual_support_status=residual_support,
        direct_sequence_evidence_component=direct_component,  # type: ignore[arg-type]
        expected_direct_effect_component=expected_component,  # type: ignore[arg-type]
        residual_evidence_component=residual_component,  # type: ignore[arg-type]
        pathway_support_component=pathway_component,  # type: ignore[arg-type]
        evidence_readiness_status=readiness,  # type: ignore[arg-type]
        targetability_fields_preserved={
            "ratio_status": "definitive"
            if direct_component != "unresolved_targetability"
            else "unresolved_missing_sequence",
            "m_targetable_transcripts": m_value,
            "targetable_fraction_m_over_n": fraction,
        },
        calibration_fields_preserved={"intended_target_calibration_value": 0.5},
        pathway_support_summary={
            "missing_pathway_evidence_interpretation": "unresolved_not_negative"
        },
        warning_codes=("upstream-warning",),
        provenance_record_ids=(f"ra-{gene}",),
    )


def classify(**kwargs):
    return compute_final_evidence_classification(
        secondary_evidence_records=[integrated_record(**kwargs)]
    ).gene_classifications[0]


def test_unresolved_upstream_integration_becomes_unresolved() -> None:
    result = compute_final_evidence_classification(
        secondary_evidence_records=[],
        secondary_unresolved_records=[
            SecondaryEvidenceIntegrationUnresolvedRecordV1(
                unresolved_record_id="sei-unresolved-1",
                gene_id="GENE",
                reason="unresolved_upstream_residual_attribution",
            )
        ],
    )
    assert result.unresolved[0].reason == "unresolved_upstream_secondary_evidence_integration"


def test_insufficient_expected_direct_effect_becomes_unresolved() -> None:
    record = classify(
        expected_component="expected_direct_effect_unavailable",
        readiness="insufficient_expected_effect_evidence",
        expected_log2=None,
    )
    assert record.final_evidence_classification == "unresolved"
    assert record.classification_confidence == "unresolved"


def test_unresolved_targetability_becomes_unresolved() -> None:
    record = classify(
        direct_component="unresolved_targetability",
        readiness="ready_with_unresolved_targetability",
        m_value=None,
        fraction=None,
    )
    assert record.final_evidence_classification == "unresolved"
    assert record.classification_reason == "unresolved_targetability"


def test_unresolved_targetability_with_negligible_no_effect_becomes_no_evidence() -> None:
    record = classify(
        direct_component="unresolved_targetability",
        expected_component="expected_direct_effect_zero",
        residual_component="no_residual_to_integrate",
        readiness="ready_with_unresolved_targetability",
        observed_log2=0.0,
        expected_log2=0.0,
        m_value=None,
        fraction=None,
    )
    assert record.final_evidence_classification == "no_evidence_for_effect"
    assert record.classification_confidence == "low"


def test_negligible_residual_and_no_expected_effect_becomes_no_evidence() -> None:
    record = classify(
        expected_component="expected_direct_effect_zero",
        observed_log2=0.0,
        expected_log2=0.0,
    )
    assert record.final_evidence_classification == "no_evidence_for_effect"
    assert record.classification_confidence == "moderate"


def test_direct_compatible_evidence_classifies_direct_compatible() -> None:
    record = classify()
    assert record.final_evidence_classification == "direct_compatible"
    assert record.classification_confidence == "high"


def test_direct_compatible_with_weak_residual_is_moderate() -> None:
    record = classify(
        residual_component="weak_residual_evidence",
        residual_magnitude="weak_residual",
        residual_log2=0.2,
        residual_support="residual_without_pathway_support",
        pathway_component="residual_without_pathway_support",
    )
    assert record.final_evidence_classification == "direct_compatible"
    assert record.classification_confidence == "moderate"


def test_secondary_supported_evidence_classifies_secondary_supported() -> None:
    record = classify(
        direct_component="no_cleavage_compatible_targetability",
        expected_component="expected_direct_effect_zero",
        residual_component="moderate_residual_evidence",
        pathway_component="residual_with_moderate_pathway_support",
        residual_support="residual_with_moderate_pathway_support",
        residual_magnitude="moderate_residual",
        residual_log2=-0.7,
        m_value=0,
        fraction=0.0,
    )
    assert record.final_evidence_classification == "secondary_supported"
    assert record.classification_confidence == "moderate"


def test_secondary_supported_strong_support_can_be_high_confidence() -> None:
    record = classify(
        direct_component="no_cleavage_compatible_targetability",
        residual_component="strong_residual_evidence",
        pathway_component="residual_with_strong_pathway_support",
        residual_support="residual_with_strong_pathway_support",
        residual_magnitude="strong_residual",
        residual_log2=-1.2,
        m_value=0,
        fraction=0.0,
    )
    assert record.final_evidence_classification == "secondary_supported"
    assert record.classification_confidence == "high"


def test_mixed_supported_evidence_classifies_mixed_supported() -> None:
    record = classify(
        residual_component="moderate_residual_evidence",
        pathway_component="residual_with_moderate_pathway_support",
        residual_support="residual_with_moderate_pathway_support",
        residual_magnitude="moderate_residual",
        residual_log2=-0.8,
    )
    assert record.final_evidence_classification == "mixed_supported"
    assert record.classification_confidence == "moderate"


def test_mixed_supported_strong_support_can_be_high_confidence() -> None:
    record = classify(
        residual_component="strong_residual_evidence",
        pathway_component="residual_with_strong_pathway_support",
        residual_support="residual_with_strong_pathway_support",
        residual_magnitude="strong_residual",
        residual_log2=-1.2,
    )
    assert record.final_evidence_classification == "mixed_supported"
    assert record.classification_confidence == "high"


def test_non_negligible_residual_with_missing_pathway_is_unresolved() -> None:
    record = classify(
        residual_component="moderate_residual_evidence",
        pathway_component="unresolved_missing_pathway_evidence",
        readiness="ready_with_unresolved_pathway_context",
        residual_magnitude="moderate_residual",
        residual_log2=-0.7,
        residual_support="unresolved_missing_pathway_evidence",
    )
    assert record.final_evidence_classification == "unresolved"
    assert record.classification_reason == "unresolved_pathway_context"


def test_non_negligible_residual_with_no_pathway_support_is_unresolved() -> None:
    record = classify(
        direct_component="no_cleavage_compatible_targetability",
        residual_component="moderate_residual_evidence",
        pathway_component="residual_without_pathway_support",
        residual_magnitude="moderate_residual",
        residual_log2=-0.7,
        residual_support="residual_without_pathway_support",
        m_value=0,
        fraction=0.0,
    )
    assert record.final_evidence_classification == "unresolved"
    assert record.classification_reason == "residual_without_pathway_support"


def test_missing_sequence_is_not_treated_as_no_targetability() -> None:
    record = classify(
        direct_component="unresolved_targetability",
        readiness="ready_with_unresolved_targetability",
        m_value=None,
        fraction=None,
    )
    assert record.final_evidence_classification == "unresolved"


def test_seed_only_evidence_is_not_upgraded() -> None:
    record = classify(
        direct_component="no_cleavage_compatible_targetability",
        expected_component="expected_direct_effect_zero",
        residual_component="no_residual_to_integrate",
        observed_log2=0.0,
        expected_log2=0.0,
        m_value=0,
        fraction=0.0,
    )
    assert record.final_evidence_classification == "no_evidence_for_effect"
    assert record.targetability_fields_preserved["m_targetable_transcripts"] == 0


def test_missing_evidence_is_never_negative_evidence() -> None:
    result = compute_final_evidence_classification(
        secondary_evidence_records=[
            integrated_record(
                direct_component="unavailable_targetability",
                readiness="ready_with_unresolved_targetability",
                m_value=None,
                fraction=None,
            )
        ]
    )
    assert result.summary["missing_evidence_as_negative"] is False


def test_forbidden_certainty_labels_are_rejected() -> None:
    payload = classify().model_dump()
    payload["classification_reason"] = "clinically_validated"
    with pytest.raises(ValueError, match="forbidden certainty"):
        GeneFinalEvidenceClassificationRecordV1.model_validate(payload)


def test_high_confidence_blocked_by_unresolved_component() -> None:
    record = classify(
        residual_component="strong_residual_evidence",
        pathway_component="unresolved_missing_pathway_evidence",
        readiness="ready_with_unresolved_pathway_context",
        residual_magnitude="strong_residual",
        residual_log2=-1.2,
        residual_support="unresolved_missing_pathway_evidence",
    )
    assert record.classification_confidence == "unresolved"


def test_interpretation_boundary_present_in_every_record() -> None:
    record = classify()
    assert record.classification_interpretation_boundary == CLASSIFICATION_INTERPRETATION_BOUNDARY


def test_invalid_policy_config_fails_clearly() -> None:
    with pytest.raises(ValueError, match="numerical_tolerance"):
        FinalEvidenceClassificationPolicyV1(numerical_tolerance=0)
    with pytest.raises(ValueError, match="missing evidence"):
        FinalEvidenceClassificationPolicyV1(missing_evidence_as_negative_allowed=True)
    with pytest.raises(ValueError, match="seed-only"):
        FinalEvidenceClassificationPolicyV1(seed_only_upgrade_allowed=True)
    with pytest.raises(ValueError, match="definitive biological"):
        FinalEvidenceClassificationPolicyV1(definitive_biological_claims_allowed=True)
    with pytest.raises(ValueError, match="regulatory"):
        FinalEvidenceClassificationPolicyV1(regulatory_claims_allowed=True)
