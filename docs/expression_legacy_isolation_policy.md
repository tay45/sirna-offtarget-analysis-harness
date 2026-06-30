# Expression Legacy Isolation Policy

Date: 2026-06-26

## Policy

Expression V2 is the only production expression contract for downstream staged analysis.

Legacy Expression V1 artifacts and legacy `ExpressionResult` precomputed
execution paths may exist only as guarded compatibility boundaries, tests, or
explicit error paths. They must not silently feed isoform, pathway, network,
transcript targetability, or planned downstream interpretation logic.

## Required Behavior

- V1 committed effect loading must fail with a typed legacy error.
- Legacy precomputed backend execution must fail with a typed legacy error.
- Precomputed differential-expression inputs must enter through `import_precomputed_expression_v2`.
- Missing adjusted p-values, condition means, replicate consistency, and shrunken fold changes must remain missing or status-coded.
- Downstream adapters may reshape V2 records into consumer-specific contracts, but must not recalculate, infer, or relabel scientific evidence.

## Enforcement

The policy is enforced by unit tests in Expression artifact, downstream, precomputed, and contract-helper suites, plus release-gate coverage and import-linter checks.
