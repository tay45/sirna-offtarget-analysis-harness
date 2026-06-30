# Isoform Uncertainty Checksum Flow Inventory

This inventory covers the `isoform_uncertainty` workflow stage only. The scientific calculation is unchanged; this pass finalizes how files are written and verified.

## Artifact Classes

Group A immutable scientific artifacts:

- `gene_isoform_uncertainty_v1.jsonl`
- `transcript_prior_weights_v1.jsonl`
- `transcript_set_exclusions_v1.jsonl`
- `transcript_annotation_validation_v1.json`
- `external_transcript_evidence_validation_v1.json`
- `isoform_method_selection_v1.json`
- `isoform_input_validation_v1.json`

Group B finalized metadata records:

- `isoform_uncertainty_run_v1.json`
- `isoform_uncertainty_result_v1.json`

Group C report views and outer commit metadata:

- `gene_isoform_uncertainty_v1.tsv`
- `transcript_prior_weights_v1.tsv`
- `transcript_set_exclusions_v1.tsv`
- `isoform_uncertainty_summary_v1.json`
- `isoform_warnings_v1.tsv`
- `stage_result.json`
- `stage_manifest.json`

## Inventory

| Artifact | Class | Writer | Rewritten | Checksum timing | Checksum stored in | Contains own checksum | Stale risk after correction | Commit manifest checksum |
|---|---:|---|---:|---|---|---:|---:|---:|
| `gene_isoform_uncertainty_v1.jsonl` | A | `write_immutable_isoform_uncertainty_artifacts` | No | After final write | run/result referenced checksums and manifest | No | No | Yes |
| `transcript_prior_weights_v1.jsonl` | A | `write_immutable_isoform_uncertainty_artifacts` | No | After final write | run/result referenced checksums and manifest | No | No | Yes |
| `transcript_set_exclusions_v1.jsonl` | A | `write_immutable_isoform_uncertainty_artifacts` | No | After final write | run/result referenced checksums and manifest | No | No | Yes |
| `transcript_annotation_validation_v1.json` | A | `write_immutable_isoform_uncertainty_artifacts` | No | After final write | run/result referenced checksums and manifest | No | No | Yes |
| `external_transcript_evidence_validation_v1.json` | A | `write_immutable_isoform_uncertainty_artifacts` | No | After final write | run/result referenced checksums and manifest | No | No | Yes |
| `isoform_method_selection_v1.json` | A | `write_immutable_isoform_uncertainty_artifacts` | No | After final write | run/result referenced checksums and manifest | No | No | Yes |
| `isoform_input_validation_v1.json` | A | `write_immutable_isoform_uncertainty_artifacts` | No | After final write | run/result referenced checksums and manifest | No | No | Yes |
| `isoform_uncertainty_run_v1.json` | B | `write_final_isoform_uncertainty_metadata` | No | After final write by outer manifest | outer manifest | No | No | Yes |
| `isoform_uncertainty_result_v1.json` | B | `write_final_isoform_uncertainty_metadata` | No | After final write by outer manifest | outer manifest | No | No | Yes |
| `isoform_uncertainty_summary_v1.json` | C report | `write_immutable_isoform_uncertainty_artifacts` | No | After final write | manifest | No | No | Yes |
| `isoform_warnings_v1.tsv` | C report | `write_immutable_isoform_uncertainty_artifacts` | No | After final write | manifest | No | No | Yes |
| `stage_result.json` | C outer contract | runner commit path | No | After final write | stage manifest `contract_sha256` and output checksum map | No | No | Yes |
| `stage_manifest.json` | C outer manifest | runner commit path | Updated as stage state changes | After committed files exist | final manifest file itself is not self-checksummed | No | No for artifact checksums | N/A |

## Correction

The old flow wrote metadata, calculated checksums, inserted those checksums into metadata, and rewrote metadata. That made internal checksum maps stale for metadata files.

The corrected flow writes Group A first, calculates Group A checksums, constructs Group B once with `referenced_artifact_checksums`, writes Group B once, verifies all final files, and then lets the committed stage manifest record the final byte checksums for every committed file.
