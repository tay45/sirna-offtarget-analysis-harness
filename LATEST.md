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

RESIDUAL ATTRIBUTION STATUS: NOT STARTED

SECONDARY-EFFECT STATUS: NOT STARTED

FINAL CLASSIFICATION STATUS: NOT STARTED

## Current Executable Pipeline

- Official terminal executable stage: residual_attribution.
- Default pipeline endpoint: residual_attribution.
- `--until-stage transcript_targetability_ratio`: verified to execute only
  validate, prepare_inputs, map_identifiers, sequence_analysis,
  expression_analysis, isoform_uncertainty, transcript_targetability, and
  transcript_targetability_ratio.
- `--until-stage expected_direct_effect`: verified to stop before residual
  support characterization.
- Full default execution additionally runs expected_direct_effect and
  residual_attribution.
- Candidate-scoring status: removed from the official package, stage registry,
  stage contracts, schemas, examples, and CLI.
- Prohibited-field scan: PASSED for current public portfolio outputs.
- Portfolio example: PASSED.
- Result summary validation: PASSED.
- Documentation synchronization: PASSED.

## Evidence

- Full test suite: passed, 597 tests.
- Full-suite exit code: 0.
- Portfolio tests: passed, 35 tests.
- Focused scientific tests: passed, 305 tests.
- Line coverage: 0.9477
- Branch coverage: 0.8502
- Source checksum: 62b5fd6e124c803e133aee5722e43be888bf765e6d2021bbc03250555edaef2d.
- Source inventory count: 644.
- Final archive filename: sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip.
- FINAL ARCHIVE CHECKSUM MODEL: EXTERNAL SIDECAR
- FINAL ARCHIVE SIDECAR: sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip.sha256
- INTERNAL SOURCE CHECKSUM: 62b5fd6e124c803e133aee5722e43be888bf765e6d2021bbc03250555edaef2d
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
residual support characterization. It stores observed normalized expression
change, N, M, M/N, intended-target calibration, expected direct effect,
unresolved residual value, residual direction, residual magnitude, and optional
pathway support separately. It does not attribute that residual to secondary
effects, produce mixed-mechanism scores, risk tiers, or final direct /
secondary / mixed classifications.

## Known Limitations

- Final residual attribution is not implemented.
- Secondary-effect integration is not implemented.
- Final classification remains planned.
- Abundance-derived transcript proportions remain deferred.
- Passenger-strand search remains unsupported.

## Next Planned Scientific Stage

Define secondary-effect integration without redefining normalized expression,
N, M, M/N, expected direct-effect evidence, or residual support characterization.
