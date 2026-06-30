# Intended Target Policy Runtime Support

`IntendedTargetValidationPolicyV1` fields actively control runtime behavior.

- `intended_target_required`: when true, a gene or transcript intended target is
  required. Missing input applies `failure_behavior`. When false and no input is
  supplied, validation records `not_requested`.
- `transcript_ids_required`: when true, gene-only input is insufficient and
  applies `failure_behavior`.
- `accepted_evidence_classes`: candidate sites outside this set are rejected.
- `maximum_total_mismatches`, `maximum_seed_mismatches`, and
  `maximum_central_mismatches`: candidate sites exceeding thresholds are
  rejected.
- `failure_behavior`: `fail_stage` fails the stage, `warning` preserves a
  warning status, and `preserve_invalid_with_status` records invalid preserved
  status without a false pass.
- `gene_only_behavior`: `preserve_uncertainty` records unresolved isoform
  identity, `warning` records a warning, `fail_stage` rejects gene-only input,
  and `accept_any_gene_transcript_site` requires an acceptable site in an
  eligible transcript of the intended gene.
- `warnings`: policy warnings are copied into the validation record.

Validation writes `intended_target_validation_v1.json` with candidate,
accepted, and rejected sites; threshold checks; sequence checks; failed-gene
checks; status; warnings; and errors.
