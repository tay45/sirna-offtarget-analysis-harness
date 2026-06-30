# Isoform Uncertainty Pre-Commit Verification

Before commit, the runner calls `verify_isoform_uncertainty_final_outputs`.

The verification:

- enumerates expected artifacts
- rejects missing required artifacts
- rejects empty artifacts unless an empty file is explicitly valid
- recomputes final checksums from final bytes
- compares run/result referenced checksums against immutable artifacts
- checks record counts for gene, weight, and exclusion JSONL files
- checks the run record is completed
- checks the result record references the finalized run
- checks metadata uses the outer-manifest self-checksum policy

If verification fails, the stage raises an error before the attempt is marked completed.
