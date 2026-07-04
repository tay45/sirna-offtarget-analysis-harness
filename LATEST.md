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

RESIDUAL SUPPORT CHARACTERIZATION STATUS: COMPLETE

RESIDUAL ATTRIBUTION STATUS: COMPLETE

SECONDARY EVIDENCE INTEGRATION STATUS: COMPLETE

SECONDARY-EFFECT STATUS: NOT STARTED

FINAL CLASSIFICATION STATUS: NOT STARTED

## Current Executable Pipeline

- Official terminal executable stage: secondary_evidence_integration.
- Default pipeline endpoint: secondary_evidence_integration.
- `--until-stage transcript_targetability_ratio`: verified to execute only
  validate, prepare_inputs, map_identifiers, sequence_analysis,
  expression_analysis, isoform_uncertainty, transcript_targetability, and
  transcript_targetability_ratio.
- `--until-stage expected_direct_effect`: verified to stop before residual
  support characterization.
- Full default execution additionally runs expected_direct_effect,
  residual_attribution, and secondary_evidence_integration.
- Candidate-scoring status: removed from the official package, stage registry,
  stage contracts, schemas, examples, and CLI.
- Prohibited-field scan: PASSED for current public portfolio outputs.
- Portfolio example: PASSED.
- Result summary validation: PASSED.
- Documentation synchronization: PASSED.

## Evidence

- Full test suite: passed, 634 tests.
- Full-suite exit code: 0.
- Portfolio tests: passed, 35 tests.
- Focused scientific tests: passed, 305 tests.
- Line coverage: 0.9480
- Branch coverage: 0.8513
- Source checksum: 9fe2a9d7eb66b864d64294dd87c2df658a41ae216675c099ef2f273ac3745122.
- Source inventory count: 644.
- Final archive filename: sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip.
- FINAL ARCHIVE CHECKSUM MODEL: EXTERNAL SIDECAR
- FINAL ARCHIVE SIDECAR: sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip.sha256
- INTERNAL SOURCE CHECKSUM: 9fe2a9d7eb66b864d64294dd87c2df658a41ae216675c099ef2f273ac3745122
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
secondary evidence integration. It stores observed normalized expression
change, N, M, M/N, intended-target calibration, expected direct effect,
unresolved residual value, residual direction, residual magnitude, optional
pathway support, and evidence readiness separately. It does not attribute that
residual to secondary effects, produce mixed-mechanism scores, risk tiers, or
final direct / secondary / mixed classifications.

## Known Limitations

- Final residual attribution is not implemented.
- Secondary evidence integration is classification-ready evidence only.
- Final classification remains planned.
- Abundance-derived transcript proportions remain deferred.
- Passenger-strand search remains unsupported.

## Next Planned Scientific Stage

Define final classification without redefining normalized expression, N, M,
M/N, expected direct-effect evidence, residual support characterization, or
secondary evidence integration.
