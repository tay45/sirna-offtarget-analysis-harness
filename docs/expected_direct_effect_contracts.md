# Expected Direct Effect Contracts

The `expected_direct_effect` stage integrates committed normalized expression
with committed transcript targetability ratios. It consumes only
`normalized_gene_effects_v2.jsonl` and
`gene_transcript_targetability_ratios_v1.jsonl`.

The intended target calibration uses the intended target's own M/N:

`raw_calibration_knockdown_fraction = (1 - 2 ** intended_target_normalized_log2fc) / intended_targetable_fraction`

The accepted calibration is used only when the intended target has a valid
normalized expression record, definitive N/M/M/N evidence, N > 0, and M/N > 0.
Values slightly outside `[0, 1]` within tolerance are normalized to the boundary;
materially out-of-bound values are preserved as raw evidence and marked
unavailable.

For each candidate with definitive ratio evidence:

`expected_direct_effect_log2fc = log2(1 - accepted_calibration_knockdown_fraction * candidate_targetable_fraction)`

The stage stores observed normalized expression, N, M, M/N, calibration,
expected direct effect, observed-versus-expected log2 difference, and
`unresolved_residual_log2fc` as separate fields. The residual is not interpreted
as a secondary effect, and the stage does not use pathway evidence or produce
direct, secondary, or mixed classifications.
