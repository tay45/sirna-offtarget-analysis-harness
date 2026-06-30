# Transcript Targetability Stage

`transcript_targetability` is a sequence-evidence stage that runs after
`isoform_uncertainty`. It validates the configured guide strand, loads a verified
transcript sequence snapshot, and searches eligible transcript sequences for ungapped
guide-complement alignments.

The stage writes transcript-level evidence records, site records, per-position alignment
match records, exclusions, policies, summary files, and verification metadata. Cleavage-
compatible full-length evidence is recorded separately from seed-only evidence.

This stage does not compute aggregate targetable transcript fractions, intended-target
knockdown calibration, direct-decrease expectations, residual models, source eligibility,
secondary-effect evidence, or final direct off-target classifications.
