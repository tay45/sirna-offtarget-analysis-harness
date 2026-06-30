# Isoform Uncertainty Artifact Finalization

The stage finalization order is:

1. Build in-memory scientific records.
2. Write immutable scientific JSON/JSONL artifacts and report views once.
3. Calculate checksums from those final files.
4. Build the completed run record with `referenced_artifact_checksums`.
5. Write `isoform_uncertainty_run_v1.json` once.
6. Build and write `isoform_uncertainty_result_v1.json` once.
7. Run pre-commit final-file verification.
8. Commit through the existing atomic staged runner.
9. Run post-commit verification before exposing the attempt as current.

The scientific records are not modified by this ordering.
