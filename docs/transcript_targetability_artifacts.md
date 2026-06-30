# Transcript Targetability Artifacts

Canonical artifacts:

- `sirna_sequence_record_v1.json`
- `sirna_sequence_validation_v1.json`
- `transcript_sequence_snapshot_validation_v1.json`
- `transcript_targetability_evidence_v1.jsonl`
- `transcript_targetability_sites_v1.jsonl`
- `transcript_targetability_mismatches_v1.jsonl`
- `transcript_targetability_exclusions_v1.jsonl`
- `transcript_targetability_policy_v1.json`
- `transcript_targetability_run_v1.json`
- `transcript_targetability_result_v1.json`
- `transcript_targetability_verification_v1.json`

Report artifacts:

- `transcript_targetability_evidence_v1.tsv`
- `transcript_targetability_sites_v1.tsv`
- `transcript_targetability_mismatches_v1.tsv`
- `transcript_targetability_exclusions_v1.tsv`
- `transcript_targetability_summary_v1.json`
- `transcript_targetability_warnings_v1.tsv`

The mismatch artifact stores every aligned guide position for each qualifying site with
`match_status` set to `match` or `mismatch`. This makes exact, near, seed-only, and
partial sequence evidence auditable without implying downstream biological effect size.
