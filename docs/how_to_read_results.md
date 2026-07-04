# How to Read Results

Start with the final evidence classification table:

`gene_final_evidence_classifications_v1.tsv`

Important columns:

- `observed_normalized_log2fc`: committed normalized gene-expression change.
- `expected_direct_effect_log2fc`: expected direct component on the log2 scale.
- `observed_vs_expected_log2_difference`: observed log2 change minus expected direct component.
- `unresolved_residual_log2fc`: preserved upstream residual.
- `residual_direction`: whether the observed change is more decreased, less decreased/increased, or matching expectation.
- `residual_magnitude_status`: negligible, weak, moderate, or strong residual magnitude.
- `residual_support_status`: support characterization only, not a final secondary-effect attribution.
- `direct_sequence_evidence_component`: sequence-derived evidence component, without seed-only upgrades.
- `expected_direct_effect_component`: expected direct-effect evidence component.
- `residual_evidence_component`: unresolved residual evidence component.
- `pathway_support_component`: optional pathway-support context component.
- `evidence_readiness_status`: readiness for a future final classification stage, not a biological call.
- `final_evidence_classification`: conservative evidence label.
- `classification_confidence`: conservative confidence label.
- `classification_reason`: rule-based reason for the evidence label.

Each gene-level classification record states that the classification is an
evidence-based interpretation of current harness outputs and is not a
definitive biological, clinical, toxicological, or regulatory conclusion.

For classification-ready upstream integration details, inspect:

`gene_secondary_evidence_integration_v1.tsv`

For upstream residual support characterization, inspect:

`gene_residual_attribution_evidence_v1.tsv`

For upstream expected direct-effect details, inspect:

`gene_expected_direct_effects_v1.tsv`

Important columns:

- `observed_normalized_log2fc`: committed normalized gene-expression change.
- `n_total_eligible_transcripts`: formal N from upstream ratio evidence.
- `m_targetable_transcripts`: formal M when definitive.
- `targetable_fraction_m_over_n`: equal-prior targetable transcript fraction.
- `intended_target_calibration_value`: accepted targetable-transcript knockdown calibration.
- `expected_direct_effect_log2fc`: expected direct component on the log2 scale.
- `observed_vs_expected_log2_difference`: observed log2 change minus expected direct component.
- `unresolved_residual_log2fc`: stored residual for the next stage, not interpreted here.

For N, M, and M/N details, inspect the ratio table:

`gene_transcript_targetability_ratios_v1.tsv`

Important columns:

- `n_total_eligible_transcripts`: formal N.
- `m_targetable_transcripts`: formal M when definitive.
- `ratio_m_over_n`: equal-prior targetable transcript fraction.
- `seed_only_transcript_count`: transcripts with seed-only evidence preserved separately.
- `unresolved_transcript_count`: transcripts whose evidence is unavailable.
- `ratio_status`: whether the M/N ratio is definitive or unavailable.

Missing sequence is not treated as proof that a transcript is non-targetable.
Seed-only evidence is preserved but excluded from default cleavage-compatible M.
