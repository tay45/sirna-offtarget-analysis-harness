# Latest Release Notes

Release date: 2026-06-28
Primary archive: sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip
Overall status: COMPLETE

Project purpose: A reproducible weight-of-evidence framework for distinguishing
direct siRNA off-target effects from downstream secondary expression changes.

PATHWAY STATUS: COMPLETE

EXPRESSION STATUS: COMPLETE

ISOFORM UNCERTAINTY STATUS: COMPLETE

TRANSCRIPT TARGETABILITY STATUS: COMPLETE

FORMAL N STATUS: COMPLETE

FORMAL M STATUS: COMPLETE

M/N STATUS: COMPLETE

PORTFOLIO INTEGRITY REPAIR STATUS: COMPLETE

FINAL RELEASE EVIDENCE REPAIR STATUS: COMPLETE

FINAL ARCHIVE CHECKSUM MODEL REPAIR STATUS: COMPLETE

INTENDED-TARGET CALIBRATION STATUS: COMPLETE

EXPECTED DIRECT EFFECT STATUS: COMPLETE

UNRESOLVED RESIDUAL VALUE STATUS: COMPLETE

RESIDUAL ATTRIBUTION STATUS: NOT STARTED

SECONDARY-EFFECT STATUS: NOT STARTED

FINAL CLASSIFICATION STATUS: NOT STARTED

## Current Executable Pipeline

- Official terminal executable stage: expected_direct_effect.
- Default pipeline endpoint: expected_direct_effect.
- `--until-stage transcript_targetability_ratio`: verified to execute only
  validate, prepare_inputs, map_identifiers, sequence_analysis,
  expression_analysis, isoform_uncertainty, transcript_targetability, and
  transcript_targetability_ratio.
- Full default execution additionally runs expected_direct_effect.
- Candidate-scoring status: removed from the official package, stage registry,
  stage contracts, schemas, examples, and CLI.
- Prohibited-field scan: PASSED for current public portfolio outputs.
- Portfolio example: PASSED.
- Result summary validation: PASSED.
- Documentation synchronization: PASSED.

## Evidence

- Full test suite: passed, 572 tests.
- Full-suite exit code: 0.
- Portfolio tests: passed, 35 tests.
- Focused scientific tests: passed, 305 tests.
- Line coverage: 0.9479
- Branch coverage: 0.8512
- Source checksum: aac43a3d8a09a73e2ad7b9830eb972eb8926c9a5a171b14f43c001fa03208f5f.
- Source inventory count: 636.
- Final archive filename: sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip.
- FINAL ARCHIVE CHECKSUM MODEL: EXTERNAL SIDECAR
- FINAL ARCHIVE SIDECAR: sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip.sha256
- INTERNAL SOURCE CHECKSUM: aac43a3d8a09a73e2ad7b9830eb972eb8926c9a5a171b14f43c001fa03208f5f
- ARCHIVE CHECKSUM: See adjacent SHA-256 sidecar file
- Post-package verification passed: true.
- Post-package verification status: PASSED.
- Clean extraction result: PASSED.
- Clean installation result: PASSED.
- Quick-start result: PASSED.
- Scientific regression result: PASSED.
- Final verification evidence filename: post_package_verification.json.
- Build, twine, and clean-wheel verification: PASSED.

## Scope

This release uses internal source integrity evidence and an adjacent external
sidecar for final archive integrity. The current validated release ends at
expected direct-effect estimation. It stores observed normalized expression
change, N, M, M/N, intended-target calibration, expected direct effect, and an
unresolved residual value separately. It does not attribute that residual to
secondary effects, produce mixed-mechanism scores, risk tiers, or final direct /
secondary / mixed classifications.

## Known Limitations

- Residual attribution is not implemented.
- Secondary-effect integration is not implemented.
- Final classification remains planned.
- Abundance-derived transcript proportions remain deferred.
- Passenger-strand search remains unsupported.

## Next Planned Scientific Stage

Interpret unresolved residuals without redefining normalized expression, N, M,
M/N, or expected direct-effect evidence.
