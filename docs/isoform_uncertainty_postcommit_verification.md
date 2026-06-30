# Isoform Uncertainty Post-Commit Verification

After commit files are written and the stage manifest is populated, the runner calls `verify_committed_isoform_uncertainty_result`.

The verifier reloads committed output files and the committed stage manifest, recomputes checksums, and compares manifest checksums with final file bytes. It detects:

- changed artifact bytes
- stale manifest checksums
- stale referenced checksums in run/result metadata
- missing artifacts
- unexpected artifacts
- count mismatches
- schema/readability failures
- run/result reference mismatches

Resume and reuse use the same committed verification path. A corrupted committed isoform uncertainty result is not reused.
