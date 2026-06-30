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

INTENDED-TARGET CALIBRATION STATUS: NOT STARTED

EXPECTED DIRECT EFFECT STATUS: NOT STARTED

RESIDUAL STATUS: NOT STARTED

SECONDARY-EFFECT STATUS: NOT STARTED

FINAL CLASSIFICATION STATUS: NOT STARTED

## Current Executable Pipeline

- Official terminal executable stage: transcript_targetability_ratio.
- Default pipeline endpoint: transcript_targetability_ratio.
- `--until-stage transcript_targetability_ratio`: verified to execute only
  validate, prepare_inputs, map_identifiers, sequence_analysis,
  expression_analysis, isoform_uncertainty, transcript_targetability, and
  transcript_targetability_ratio.
- Candidate-scoring status: removed from the official package, stage registry,
  stage contracts, schemas, examples, and CLI.
- Prohibited-field scan: PASSED for current public portfolio outputs.
- Portfolio example: PASSED.
- Result summary validation: PASSED.
- Documentation synchronization: PASSED.

## Evidence

- Full test suite: passed, 528 tests.
- Full-suite exit code: 0.
- Portfolio tests: passed, 35 tests.
- Focused scientific tests: passed, 305 tests.
- Line coverage: 0.9482.
- Branch coverage: 0.8502.
- Source checksum: d9ba8b83cb7086f3df94cfe3eca45cbb06b48d884a4a5076494cb7a6ed519048.
- Source inventory count: 627.
- Final archive filename: sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip.
- FINAL ARCHIVE CHECKSUM MODEL: EXTERNAL SIDECAR
- FINAL ARCHIVE SIDECAR: sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip.sha256
- INTERNAL SOURCE CHECKSUM: d9ba8b83cb7086f3df94cfe3eca45cbb06b48d884a4a5076494cb7a6ed519048
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

This repair fixes final archive checksum evidence semantics. The ZIP uses
internal source integrity evidence and an adjacent external sidecar for final
archive integrity. The current validated release ends at formal transcript
targetability ratio estimation and verification. It does not produce
direct-effect scores, secondary-effect scores, mixed-mechanism scores, risk
tiers, or final direct / secondary / mixed classifications.

## Known Limitations

- Intended-target knockdown calibration is not implemented.
- Expected direct-effect estimation is not implemented.
- Residual attribution is not implemented.
- Secondary-effect integration is not implemented.
- Final classification remains planned.
- Abundance-derived transcript proportions remain deferred.
- Passenger-strand search remains unsupported.

## Next Planned Scientific Stage

Define intended-target knockdown calibration without redefining formal N, M, or
M/N.
