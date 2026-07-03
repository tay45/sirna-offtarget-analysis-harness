from __future__ import annotations

from math import isclose, log2

from sirna_offtarget.expected_direct_effect.contracts import ExpectedDirectEffectPolicyV1
from sirna_offtarget.expected_direct_effect.core import compute_expected_direct_effects
from sirna_offtarget.expression.contracts_v2 import NormalizedGeneEffectRecordV2
from sirna_offtarget.transcript_targetability_ratio.contracts import (
    GeneTranscriptTargetabilityRatioRecordV1,
)


def expr(gene: str, log2fc: float | None, *, canonical: str | None = None):
    return NormalizedGeneEffectRecordV2(
        schema_version="2",
        record_id=f"expr-{gene}",
        original_gene_id=gene,
        original_gene_namespace="symbol",
        canonical_gene_id=canonical if canonical is not None else gene,
        approved_symbol=gene,
        identifier_resolution_id=f"ids-{gene}",
        identifier_mapping_confidence=1.0,
        identifier_ambiguity_status="unambiguous",
        identifier_organism_match=True,
        organism="synthetic",
        contrast_id="treated_vs_control",
        normalization_run_id="expr-run",
        input_mode="precomputed_de",
        input_value_scale="normalized",
        normalization_method="imported",
        differential_method="imported",
        effect_scale="log2_fold_change",
        raw_effect_estimate=log2fc,
        reported_log2_fold_change=log2fc,
        shrunken_log2_fold_change=None,
        canonical_log2_fold_change=log2fc,
        canonical_effect_source="reported_unshrunken_log2fc",
        standard_error=None,
        confidence_interval_lower=None,
        confidence_interval_upper=None,
        test_statistic=None,
        raw_p_value=None,
        adjusted_p_value=None,
        adjusted_pvalue_status="adjusted_pvalue_unavailable",
        multiple_testing_method="none",
        tested_status="tested",
        filter_status="not_filtered",
        low_count_status="not_imported",
        model_status="estimated",
        exclusion_reason=None,
        numerical_direction="decreased" if log2fc is not None and log2fc < 0 else "unchanged",
        statistical_support_status="not_tested",
        biological_threshold_status="not_evaluated",
        direction_basis="canonical_log2_fold_change",
        control_abundance_summary=None,
        treatment_abundance_summary=None,
        mean_abundance_summary=None,
        replicate_count_control=None,
        replicate_count_treatment=None,
        design_formula="~ condition",
        covariates=(),
        batch_terms=(),
        analysis_software="fixture",
        analysis_software_version="1",
        provenance_record_ids=(),
        source_row_identifier=f"row-{gene}",
    )


def ratio(
    gene: str,
    n: int,
    m: int | None,
    *,
    status: str = "definitive",
    seed_only: tuple[str, ...] = (),
):
    value = None if m is None or status != "definitive" else m / n
    return GeneTranscriptTargetabilityRatioRecordV1(
        ratio_record_id=f"ratio-{gene}",
        canonical_gene_id=gene,
        source_isoform_uncertainty_record_id=f"iso-{gene}",
        source_targetability_result_id="tt-run",
        targetability_inclusion_policy_id="targetable-transcript-inclusion-v1-cleavage-compatible",
        eligible_transcript_ids=tuple(f"{gene}-tx{i}" for i in range(n)),
        n_total_eligible_transcripts=n,
        evaluable_transcript_ids=tuple(f"{gene}-tx{i}" for i in range(n)),
        n_evaluable_transcripts=n,
        unresolved_transcript_ids=() if status == "definitive" else (f"{gene}-tx0",),
        unresolved_transcript_count=0 if status == "definitive" else 1,
        qualifying_transcript_ids=tuple(f"{gene}-tx{i}" for i in range(m or 0)),
        observed_qualifying_transcript_count=m or 0,
        m_targetable_transcripts=m,
        m_status=status,
        ratio_m_over_n=value,
        ratio_status=status,
        ratio_unavailable_reason=None if status == "definitive" else status,
        equal_prior_weight_per_transcript=1 / n,
        qualifying_equal_prior_weight_sum=value,
        equal_prior_consistency_status="passed" if status == "definitive" else "not_applicable",
        seed_only_transcript_ids=seed_only,
        seed_only_transcript_count=len(seed_only),
    )


def run_case(target_lfc: float, target_ratio, candidate_ratio, candidate_lfc: float = -0.5):
    return compute_expected_direct_effects(
        intended_target_gene_id="TARGET",
        expression_records=[expr("TARGET", target_lfc), expr("GENE", candidate_lfc)],
        ratio_records=[target_ratio, candidate_ratio],
        policy=ExpectedDirectEffectPolicyV1(numerical_tolerance=1e-9),
    )


def gene_record(computation, gene: str = "GENE"):
    return {record.canonical_gene_id: record for record in computation.gene_effects}[gene]


def test_calibration_with_intended_target_m_over_n_one() -> None:
    computation = run_case(log2(0.5), ratio("TARGET", 2, 2), ratio("GENE", 2, 1))
    assert computation.calibration.status == "definitive"
    assert computation.calibration.raw_calibration_knockdown_fraction == 0.5
    assert computation.calibration.accepted_calibration_knockdown_fraction == 0.5


def test_calibration_with_partial_intended_target_m_over_n() -> None:
    computation = run_case(log2(0.75), ratio("TARGET", 2, 1), ratio("GENE", 2, 1))
    assert computation.calibration.status == "definitive"
    assert isclose(computation.calibration.accepted_calibration_knockdown_fraction or -1, 0.5)


def test_intended_target_m_over_n_zero_is_unavailable() -> None:
    computation = run_case(log2(0.75), ratio("TARGET", 2, 0), ratio("GENE", 2, 1))
    assert computation.calibration.status == "unavailable_intended_target_ratio"
    assert computation.calibration.accepted_calibration_knockdown_fraction is None
    assert gene_record(computation).status == "unavailable_calibration"


def test_intended_target_ratio_unresolved_is_unavailable() -> None:
    computation = run_case(
        log2(0.75),
        ratio("TARGET", 2, None, status="unavailable_incomplete_evidence"),
        ratio("GENE", 2, 1),
    )
    assert computation.calibration.status == "unavailable_intended_target_ratio"


def test_intended_target_no_expression_change_has_zero_calibration() -> None:
    computation = run_case(0.0, ratio("TARGET", 2, 1), ratio("GENE", 2, 1), 0.0)
    record = gene_record(computation)
    assert computation.calibration.status == "definitive_zero_no_decrease"
    assert record.expected_direct_effect_log2fc == 0
    assert record.unresolved_residual_log2fc == 0


def test_intended_target_increase_does_not_infer_negative_knockdown() -> None:
    computation = run_case(0.25, ratio("TARGET", 2, 1), ratio("GENE", 2, 1))
    assert computation.calibration.status == "unavailable_not_decreased"
    assert computation.calibration.accepted_calibration_knockdown_fraction is None


def test_raw_calibration_exactly_one_is_accepted() -> None:
    computation = run_case(log2(0.5), ratio("TARGET", 2, 1), ratio("GENE", 2, 2))
    assert computation.calibration.raw_calibration_knockdown_fraction == 1
    assert computation.calibration.accepted_calibration_knockdown_fraction == 1


def test_raw_calibration_slightly_above_one_within_tolerance_is_normalized() -> None:
    policy = ExpectedDirectEffectPolicyV1(numerical_tolerance=1e-6)
    computation = compute_expected_direct_effects(
        intended_target_gene_id="TARGET",
        expression_records=[expr("TARGET", log2(0.4999999999)), expr("GENE", -0.5)],
        ratio_records=[ratio("TARGET", 2, 1), ratio("GENE", 2, 1)],
        policy=policy,
    )
    assert computation.calibration.raw_calibration_knockdown_fraction is not None
    assert computation.calibration.raw_calibration_knockdown_fraction > 1
    assert computation.calibration.accepted_calibration_knockdown_fraction == 1


def test_raw_calibration_materially_above_one_is_unavailable() -> None:
    computation = run_case(log2(0.25), ratio("TARGET", 2, 1), ratio("GENE", 2, 1))
    assert computation.calibration.status == "unavailable_inconsistent_calibration"
    assert "calibration_exceeds_model_bound" in computation.calibration.warning_codes
    assert computation.calibration.accepted_calibration_knockdown_fraction is None


def test_missing_intended_target_expression() -> None:
    computation = compute_expected_direct_effects(
        intended_target_gene_id="TARGET",
        expression_records=[expr("GENE", -0.5)],
        ratio_records=[ratio("TARGET", 2, 1), ratio("GENE", 2, 1)],
    )
    assert computation.calibration.status == "unavailable_missing_expression"


def test_invalid_intended_target_identifier() -> None:
    computation = compute_expected_direct_effects(
        intended_target_gene_id="TARGET",
        expression_records=[expr("TARGET", -0.5), expr("GENE", -0.5)],
        ratio_records=[ratio("GENE", 2, 1)],
    )
    assert computation.calibration.status == "unavailable_invalid_intended_target"


def test_candidate_m_over_n_zero_produces_zero_expected_effect() -> None:
    computation = run_case(log2(0.5), ratio("TARGET", 2, 2), ratio("GENE", 2, 0))
    record = gene_record(computation)
    assert record.status == "definitive"
    assert record.expected_direct_effect_log2fc == 0


def test_candidate_partial_m_over_n_expected_effect() -> None:
    computation = run_case(log2(0.5), ratio("TARGET", 2, 2), ratio("GENE", 2, 1))
    record = gene_record(computation)
    assert isclose(record.expected_direct_effect_log2fc or 0, log2(0.75))


def test_candidate_m_over_n_one_uses_calibrated_targetable_effect() -> None:
    computation = run_case(log2(0.5), ratio("TARGET", 2, 2), ratio("GENE", 2, 2))
    record = gene_record(computation)
    assert record.expected_direct_effect_log2fc == log2(0.5)


def test_candidate_missing_sequence_remains_unresolved() -> None:
    computation = run_case(
        log2(0.5),
        ratio("TARGET", 2, 2),
        ratio("GENE", 2, None, status="unavailable_incomplete_evidence"),
    )
    record = gene_record(computation)
    assert record.status == "unavailable_ratio"
    assert record.unresolved_reason == "unavailable_incomplete_evidence"


def test_seed_only_evidence_stays_excluded_from_m() -> None:
    computation = run_case(
        log2(0.5),
        ratio("TARGET", 2, 2),
        ratio("GENE", 2, 0, seed_only=("GENE-tx0",)),
    )
    record = gene_record(computation)
    assert record.m_targetable_transcripts == 0
    assert record.targetable_fraction_m_over_n == 0
    assert record.expected_direct_effect_log2fc == 0


def test_no_expression_change_preserves_zero_residual() -> None:
    computation = run_case(log2(0.5), ratio("TARGET", 2, 2), ratio("GENE", 2, 0), 0.0)
    assert gene_record(computation).unresolved_residual_log2fc == 0


def test_partial_knockdown_candidate_residual_sign_is_preserved() -> None:
    computation = run_case(log2(0.75), ratio("TARGET", 2, 1), ratio("GENE", 2, 1), -0.5)
    record = gene_record(computation)
    assert record.observed_vs_expected_log2_difference is not None
    assert record.observed_vs_expected_log2_difference < 0


def test_observed_decrease_smaller_than_expected_preserves_positive_residual() -> None:
    computation = run_case(log2(0.5), ratio("TARGET", 2, 2), ratio("GENE", 2, 2), -0.25)
    record = gene_record(computation)
    assert record.observed_vs_expected_log2_difference is not None
    assert record.observed_vs_expected_log2_difference > 0
