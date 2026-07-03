from __future__ import annotations

import pytest

from sirna_offtarget.expected_direct_effect.contracts import GeneExpectedDirectEffectRecordV1
from sirna_offtarget.residual_attribution.contracts import ResidualAttributionPolicyV1
from sirna_offtarget.residual_attribution.core import (
    PathwaySupportEvidence,
    compute_residual_attribution,
)


def expected_record(
    gene: str = "GENE",
    residual: float | None = 0.0,
    *,
    status: str = "definitive",
    seed_only: bool = False,
) -> GeneExpectedDirectEffectRecordV1:
    return GeneExpectedDirectEffectRecordV1(
        expected_direct_effect_record_id=f"ede-{gene}",
        canonical_gene_id=gene,
        approved_symbol=gene,
        source_expression_record_id=f"expr-{gene}",
        source_ratio_record_id=f"ratio-{gene}",
        source_calibration_record_id="calibration-1",
        observed_normalized_log2fc=residual if residual is not None else None,
        n_total_eligible_transcripts=2,
        m_targetable_transcripts=0 if seed_only else 1,
        targetable_fraction_m_over_n=0.0 if seed_only else 0.5,
        ratio_status="definitive",
        intended_target_calibration_value=0.5,
        expected_remaining_fraction=0.75,
        expected_direct_effect_log2fc=0.0 if residual is not None else None,
        observed_vs_expected_log2_difference=residual,
        unresolved_residual_log2fc=residual,
        status=status,  # type: ignore[arg-type]
        unresolved_reason=None if status == "definitive" else "unavailable_calibration",
        provenance_record_ids=(f"expr-{gene}", f"ratio-{gene}", "calibration-1"),
    )


def first_record(**kwargs):
    return compute_residual_attribution(
        expected_direct_effect_records=[expected_record(**kwargs)],
        pathway_evidence_available=True,
    ).gene_evidence[0]


def test_zero_residual_has_no_residual_to_attribute() -> None:
    record = first_record(residual=0.0)
    assert record.residual_direction == "matches_expected_direct_effect"
    assert record.residual_magnitude_status == "negligible_residual"
    assert record.residual_support_status == "no_residual_to_attribute"


def test_residual_below_negligible_threshold_has_no_residual_to_attribute() -> None:
    record = first_record(residual=0.05)
    assert record.residual_magnitude_status == "negligible_residual"
    assert record.residual_support_status == "no_residual_to_attribute"


def test_weak_moderate_and_strong_residual_magnitudes() -> None:
    assert first_record(residual=0.2).residual_magnitude_status == "weak_residual"
    assert first_record(residual=0.5).residual_magnitude_status == "moderate_residual"
    assert first_record(residual=1.0).residual_magnitude_status == "strong_residual"


def test_negative_and_positive_residual_direction() -> None:
    assert first_record(residual=-0.2).residual_direction == "more_decreased_than_expected"
    assert (
        first_record(residual=0.2).residual_direction == "less_decreased_or_increased_than_expected"
    )


def test_upstream_unresolved_expected_effect_takes_precedence() -> None:
    result = compute_residual_attribution(
        expected_direct_effect_records=[
            expected_record(residual=None, status="unavailable_calibration")
        ],
        pathway_evidence_available=True,
    )
    assert not result.gene_evidence
    assert result.unresolved[0].reason == "unresolved_upstream_expected_effect"


def test_missing_pathway_evidence_is_unresolved_not_negative() -> None:
    result = compute_residual_attribution(
        expected_direct_effect_records=[expected_record(residual=0.2)],
        pathway_evidence_available=False,
    )
    record = result.gene_evidence[0]
    assert record.residual_support_status == "unresolved_missing_pathway_evidence"
    assert result.unresolved[0].reason == "unresolved_missing_pathway_evidence"
    assert (
        record.pathway_support_summary["missing_pathway_evidence_interpretation"]
        == "unresolved_not_negative"
    )


def test_available_pathway_artifact_without_support_is_not_supported() -> None:
    record = first_record(residual=0.2)
    assert record.residual_support_status == "residual_without_pathway_support"


def test_pathway_support_increases_support_category_without_classification() -> None:
    result = compute_residual_attribution(
        expected_direct_effect_records=[expected_record(residual=0.2)],
        pathway_support_by_gene={
            "GENE": [
                PathwaySupportEvidence("path-1", "signed_path"),
                PathwaySupportEvidence("path-2", "shared_membership"),
            ]
        },
        pathway_evidence_available=True,
    )
    record = result.gene_evidence[0]
    assert record.residual_support_status == "residual_with_moderate_pathway_support"
    assert record.interpretation_boundary.endswith("calling_remains_planned")


def test_single_pathway_support_record_is_weak_support() -> None:
    result = compute_residual_attribution(
        expected_direct_effect_records=[expected_record(residual=0.2)],
        pathway_support_by_gene={"GENE": [PathwaySupportEvidence("path-1", "signed_path")]},
        pathway_evidence_available=True,
    )
    assert result.gene_evidence[0].residual_support_status == "residual_with_weak_pathway_support"


def test_strong_pathway_support_status() -> None:
    result = compute_residual_attribution(
        expected_direct_effect_records=[expected_record(residual=0.2)],
        pathway_support_by_gene={
            "GENE": [PathwaySupportEvidence(f"path-{index}", "signed_path") for index in range(4)]
        },
        pathway_evidence_available=True,
    )
    assert result.gene_evidence[0].residual_support_status == "residual_with_strong_pathway_support"


def test_seed_only_targetability_fields_are_preserved_not_upgraded() -> None:
    record = first_record(residual=0.2, seed_only=True)
    assert record.targetability_fields_preserved["m_targetable_transcripts"] == 0
    assert record.targetability_fields_preserved["targetable_fraction_m_over_n"] == 0.0


def test_residual_sign_is_preserved() -> None:
    record = first_record(residual=-0.75)
    assert record.unresolved_residual_log2fc == -0.75
    assert record.observed_vs_expected_log2_difference == -0.75
    assert record.residual_abs_log2 == 0.75


def test_threshold_boundary_behavior() -> None:
    policy = ResidualAttributionPolicyV1(
        negligible_residual_abs_log2_threshold=0.1,
        moderate_residual_abs_log2_threshold=0.5,
        strong_residual_abs_log2_threshold=1.0,
    )
    result = compute_residual_attribution(
        expected_direct_effect_records=[expected_record(residual=0.1)],
        pathway_evidence_available=True,
        policy=policy,
    )
    assert result.gene_evidence[0].residual_magnitude_status == "negligible_residual"


def test_invalid_threshold_config_fails_clearly() -> None:
    with pytest.raises(ValueError, match="moderate residual threshold"):
        ResidualAttributionPolicyV1(
            negligible_residual_abs_log2_threshold=0.5,
            moderate_residual_abs_log2_threshold=0.5,
        )


def test_invalid_negative_negligible_threshold_fails_clearly() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ResidualAttributionPolicyV1(negligible_residual_abs_log2_threshold=-0.1)


def test_invalid_strong_threshold_fails_clearly() -> None:
    with pytest.raises(ValueError, match="strong residual threshold"):
        ResidualAttributionPolicyV1(
            moderate_residual_abs_log2_threshold=1.0,
            strong_residual_abs_log2_threshold=1.0,
        )


def test_classification_and_targetability_override_guardrails() -> None:
    with pytest.raises(ValueError, match="final classification"):
        ResidualAttributionPolicyV1(classification_performed=True)
    with pytest.raises(ValueError, match="override sequence targetability"):
        ResidualAttributionPolicyV1(sequence_targetability_override=True)


def test_invalid_pathway_support_thresholds_fail_clearly() -> None:
    with pytest.raises(ValueError, match="pathway support count thresholds"):
        ResidualAttributionPolicyV1(
            weak_pathway_support_min_count=2,
            moderate_pathway_support_min_count=1,
        )


def test_malformed_definitive_upstream_record_is_unresolved() -> None:
    malformed = expected_record(residual=0.2).model_copy(
        update={"observed_normalized_log2fc": None}
    )
    result = compute_residual_attribution(
        expected_direct_effect_records=[malformed],
        pathway_evidence_available=True,
    )
    assert not result.gene_evidence
    assert result.unresolved[0].reason == "unresolved_upstream_expected_effect"
