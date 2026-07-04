from __future__ import annotations

import pytest

from sirna_offtarget.residual_attribution.contracts import (
    GeneResidualAttributionEvidenceRecordV1,
    ResidualAttributionUnresolvedRecordV1,
)
from sirna_offtarget.secondary_evidence_integration.contracts import (
    INTERPRETATION_BOUNDARY,
    GeneSecondaryEvidenceIntegrationRecordV1,
    SecondaryEvidenceIntegrationPolicyV1,
)
from sirna_offtarget.secondary_evidence_integration.core import (
    compute_secondary_evidence_integration,
)


def residual_record(
    gene: str = "GENE",
    *,
    residual: float = 0.2,
    magnitude: str = "weak_residual",
    support_status: str = "unresolved_missing_pathway_evidence",
    ratio_status: str | None = "definitive",
    n_value: int | None = 2,
    m_value: int | None = 1,
    fraction: float | None = 0.5,
    expected_log2: float = -0.4,
) -> GeneResidualAttributionEvidenceRecordV1:
    return GeneResidualAttributionEvidenceRecordV1(
        residual_attribution_record_id=f"ra-{gene}",
        gene_id=gene,
        expected_direct_effect_record_id=f"ede-{gene}",
        observed_normalized_log2fc=-0.2,
        expected_direct_effect_log2fc=expected_log2,
        observed_vs_expected_log2_difference=residual,
        unresolved_residual_log2fc=residual,
        residual_abs_log2=abs(residual),
        residual_direction=(
            "more_decreased_than_expected"
            if residual < 0
            else "less_decreased_or_increased_than_expected"
        ),
        residual_magnitude_status=magnitude,  # type: ignore[arg-type]
        pathway_support_summary={
            "pathway_evidence_available": support_status != "unresolved_missing_pathway_evidence",
            "missing_pathway_evidence_interpretation": "unresolved_not_negative",
            "supporting_context_only": True,
        },
        residual_support_status=support_status,  # type: ignore[arg-type]
        targetability_fields_preserved={
            "source_ratio_record_id": f"ratio-{gene}",
            "n_total_eligible_transcripts": n_value,
            "m_targetable_transcripts": m_value,
            "targetable_fraction_m_over_n": fraction,
            "ratio_status": ratio_status,
        },
        intended_target_calibration_value=0.5,
        provenance_record_ids=(f"ede-{gene}",),
    )


def first_record(**kwargs):
    return compute_secondary_evidence_integration(
        residual_attribution_records=[residual_record(**kwargs)],
    ).gene_evidence[0]


def test_definitive_residual_attribution_produces_integrated_evidence_record() -> None:
    record = first_record(support_status="residual_without_pathway_support")
    assert record.direct_sequence_evidence_component == "definitive_targetable_fraction_present"
    assert record.expected_direct_effect_component == "expected_direct_effect_nonzero"
    assert record.residual_evidence_component == "weak_residual_evidence"
    assert record.pathway_support_component == "residual_without_pathway_support"
    assert record.evidence_readiness_status == "ready_for_final_classification"


def test_upstream_residual_attribution_unresolved_produces_unresolved_record() -> None:
    result = compute_secondary_evidence_integration(
        residual_attribution_records=[],
        residual_unresolved_records=[
            ResidualAttributionUnresolvedRecordV1(
                unresolved_record_id="unresolved-1",
                gene_id="GENE",
                reason="unresolved_upstream_expected_effect",
                preserved_upstream_status="unavailable_calibration",
            )
        ],
    )
    assert not result.gene_evidence
    assert result.unresolved[0].reason == "unresolved_upstream_residual_attribution"


def test_expected_direct_effect_zero_and_nonzero_components() -> None:
    assert (
        first_record(expected_log2=0.0).expected_direct_effect_component
        == "expected_direct_effect_zero"
    )
    assert (
        first_record(expected_log2=-0.2).expected_direct_effect_component
        == "expected_direct_effect_nonzero"
    )


def test_expected_direct_effect_unavailable_produces_insufficient_expected_effect_evidence() -> (
    None
):
    source = residual_record().model_copy(update={"expected_direct_effect_log2fc": None})
    result = compute_secondary_evidence_integration(residual_attribution_records=[source])
    record = result.gene_evidence[0]
    assert record.expected_direct_effect_component == "expected_direct_effect_unavailable"
    assert record.evidence_readiness_status == "insufficient_expected_effect_evidence"


def test_unresolved_targetability_produces_ready_with_unresolved_targetability() -> None:
    record = first_record(ratio_status="unresolved_missing_sequence", m_value=None, fraction=None)
    assert record.direct_sequence_evidence_component == "unresolved_targetability"
    assert record.evidence_readiness_status == "ready_with_unresolved_targetability"


def test_unavailable_targetability_produces_ready_with_unresolved_targetability() -> None:
    record = first_record(ratio_status=None, m_value=None, fraction=None)
    assert record.direct_sequence_evidence_component == "unavailable_targetability"
    assert record.evidence_readiness_status == "ready_with_unresolved_targetability"


def test_fraction_only_targetability_is_preserved_as_targetable_fraction_present() -> None:
    record = first_record(m_value=None, fraction=0.25)
    assert record.direct_sequence_evidence_component == "definitive_targetable_fraction_present"
    assert record.targetability_fields_preserved["targetable_fraction_m_over_n"] == 0.25


def test_missing_pathway_context_with_non_negligible_residual_is_ready_with_context_gap() -> None:
    record = first_record(
        support_status="unresolved_missing_pathway_evidence",
        magnitude="weak_residual",
    )
    assert record.pathway_support_component == "unresolved_missing_pathway_evidence"
    assert record.evidence_readiness_status == "ready_with_unresolved_pathway_context"


def test_negligible_residual_does_not_require_pathway_context() -> None:
    record = first_record(
        residual=0.0,
        magnitude="negligible_residual",
        support_status="no_residual_to_attribute",
    )
    assert record.residual_evidence_component == "no_residual_to_integrate"
    assert record.evidence_readiness_status == "ready_for_final_classification"


def test_seed_only_evidence_is_not_upgraded() -> None:
    record = first_record(m_value=0, fraction=0.0)
    assert record.direct_sequence_evidence_component == "no_cleavage_compatible_targetability"
    assert record.targetability_fields_preserved["m_targetable_transcripts"] == 0


def test_missing_sequence_is_not_treated_as_non_targetable() -> None:
    record = first_record(ratio_status="unresolved_missing_sequence", n_value=None, m_value=None)
    assert record.direct_sequence_evidence_component == "unresolved_targetability"


def test_residual_sign_and_upstream_values_are_preserved() -> None:
    source = residual_record(residual=-0.75, magnitude="moderate_residual")
    record = compute_secondary_evidence_integration(
        residual_attribution_records=[source],
    ).gene_evidence[0]
    assert record.unresolved_residual_log2fc == source.unresolved_residual_log2fc
    assert (
        record.observed_vs_expected_log2_difference == source.observed_vs_expected_log2_difference
    )
    assert record.residual_direction == source.residual_direction
    assert record.residual_magnitude_status == source.residual_magnitude_status


def test_pathway_support_status_is_preserved() -> None:
    record = first_record(support_status="residual_with_strong_pathway_support")
    assert record.residual_support_status == "residual_with_strong_pathway_support"
    assert record.pathway_support_component == "residual_with_strong_pathway_support"


def test_strong_residual_component_is_preserved() -> None:
    record = first_record(magnitude="strong_residual")
    assert record.residual_evidence_component == "strong_residual_evidence"


def test_unresolved_residual_evidence_is_insufficient() -> None:
    source = residual_record().model_copy(
        update={"unresolved_residual_log2fc": None, "residual_magnitude_status": None}
    )
    record = compute_secondary_evidence_integration(
        residual_attribution_records=[source]
    ).gene_evidence[0]
    assert record.residual_evidence_component == "unresolved_residual_evidence"
    assert record.evidence_readiness_status == "insufficient_residual_evidence"


def test_unknown_pathway_status_is_treated_as_unresolved_upstream() -> None:
    source = residual_record().model_copy(update={"residual_support_status": "unexpected_status"})
    record = compute_secondary_evidence_integration(
        residual_attribution_records=[source]
    ).gene_evidence[0]
    assert record.pathway_support_component == "unresolved_upstream_expected_effect"
    assert record.evidence_readiness_status == "unresolved_upstream_residual_attribution"


def test_interpretation_boundary_is_present_in_every_record() -> None:
    record = first_record()
    assert record.interpretation_boundary == INTERPRETATION_BOUNDARY


def test_forbidden_final_classification_fields_are_not_allowed() -> None:
    payload = first_record().model_dump()
    payload["pathway_support_summary"] = {"final_classification": "forbidden"}
    with pytest.raises(ValueError, match="final call fields"):
        GeneSecondaryEvidenceIntegrationRecordV1.model_validate(payload)


def test_invalid_policy_config_fails_clearly() -> None:
    with pytest.raises(ValueError, match="numerical_tolerance"):
        SecondaryEvidenceIntegrationPolicyV1(numerical_tolerance=0)
    with pytest.raises(ValueError, match="must not perform"):
        SecondaryEvidenceIntegrationPolicyV1(classification_performed=True)
    with pytest.raises(ValueError, match="classification is not allowed"):
        SecondaryEvidenceIntegrationPolicyV1(classification_allowed=True)
    with pytest.raises(ValueError, match="seed-only evidence"):
        SecondaryEvidenceIntegrationPolicyV1(seed_only_upgrade_allowed=True)
    with pytest.raises(ValueError, match="missing evidence"):
        SecondaryEvidenceIntegrationPolicyV1(missing_evidence_as_negative_allowed=True)
