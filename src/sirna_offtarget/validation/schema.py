from __future__ import annotations


def required_output_files() -> set[str]:
    return {
        "gene_transcript_targetability_ratios_v1.tsv",
        "targetable_transcript_inclusion_policy_v1.json",
        "transcript_m_contributions_v1.tsv",
        "transcript_targetability_ratio_result_v1.json",
        "transcript_targetability_ratio_summary_v1.json",
        "transcript_targetability_ratio_verification_v1.json",
        "expected_direct_effect_result_v1.json",
        "expected_direct_effect_summary_v1.json",
        "expected_direct_effect_verification_v1.json",
        "gene_expected_direct_effects_v1.tsv",
        "intended_target_knockdown_calibration_v1.json",
    }
