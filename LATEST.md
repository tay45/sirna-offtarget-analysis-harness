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

FINAL EVIDENCE CLASSIFICATION STATUS: COMPLETE

EXTERNAL BENCHMARK VALIDATION STATUS: NOT STARTED

## Current Executable Pipeline

- Official terminal executable stage: final_evidence_classification.
- Default pipeline endpoint: final_evidence_classification.
- `--until-stage transcript_targetability_ratio`: verified to execute only
  validate, prepare_inputs, map_identifiers, sequence_analysis,
  expression_analysis, isoform_uncertainty, transcript_targetability, and
  transcript_targetability_ratio.
- `--until-stage expected_direct_effect`: verified to stop before residual
  support characterization.
- Full default execution additionally runs expected_direct_effect,
  residual_attribution, secondary_evidence_integration, and
  final_evidence_classification.
- Candidate-scoring status: removed from the official package, stage registry,
  stage contracts, schemas, examples, and CLI.
- Prohibited-field scan: PASSED for current public portfolio outputs.
- Portfolio example: PASSED.
- Result summary validation: PASSED.
- Documentation synchronization: PASSED.

## Evidence

- Full test suite: passed, 669 tests.
- Full-suite exit code: 0.
- Portfolio tests: passed, 35 tests.
- Focused scientific tests: passed, 305 tests.
- Line coverage: 0.9476
- Branch coverage: 0.8504
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
final evidence classification. It stores observed normalized expression change,
N, M, M/N, intended-target calibration, expected direct effect, unresolved
residual value, residual direction, residual magnitude, optional pathway
support, evidence readiness, and conservative evidence classification labels.
The labels are evidence-based interpretations, not definitive biological,
clinical, toxicological, or regulatory conclusions.
The current release uses deterministic, rule-based, evidence-preserving
classification. ML-assisted evidence weighting is future benchmark-dependent
work only.

## Known Limitations

- Final evidence classification is implemented as conservative evidence labels.
- External benchmark validation remains planned.
- Calibration against real perturbation datasets remains planned.
- Confidence calibration, optional ML-assisted evidence weighting, and
  statistical/ML model comparison remain future benchmark-dependent work.
- Abundance-derived transcript proportions remain deferred.
- Passenger-strand search remains unsupported.

## Next Planned Scientific Stage

Validate final evidence classification against external benchmark perturbation
datasets before any confidence calibration, optional ML-assisted evidence
weighting, statistical/ML model comparison, or optional model tuning.
