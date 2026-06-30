# Expression Branch Coverage Gap Inventory

Date: 2026-06-26

## Baseline

Fresh baseline coverage from the supplied archive passed the 92% line gate but failed the required branch gate:

- Tests: 274 passed.
- Line coverage: 92.10%.
- Branch coverage: 81.96%.
- Notable Expression gaps: committed V2 loader edge cases, downstream exclusion states, precomputed status helper states, and V2 null-preservation branches.

## Completed Gap Closure

This pass closed Expression-relevant branch gaps with tests for:

- Committed Expression V2 current pointer formats, missing manifests, terminal statuses, partial attempts, checksum mismatch, uncommitted artifacts, and V1 rejection.
- Downstream V2 consumer handling for missing canonical effects, unresolved genes, ambiguous identifiers, model failure, model-not-estimable, unsupported filter states, missing adjusted p-values, missing condition means, missing replicate consistency, and shrinkage status.
- Expression V2 status helpers that preserve explicit unavailable states instead of inventing numeric values.
- Legacy precomputed backend isolation.

The global branch gate also required non-scientific infrastructure coverage, so this pass added tests for contract validation, checkpoint/current pointer helpers, provider response metadata validation, hashing helpers, attempt listing, and output directory validation.

## Final Coverage

- Tests: 313 passed.
- Coverage command: `.venv/bin/python -m pytest --cov=src/sirna_offtarget --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=92`.
- Threshold command: `.venv/bin/python scripts/check_coverage_thresholds.py coverage.xml --min-line-rate 0.92 --min-branch-rate 0.85`.
- Threshold result: line-rate 0.9530, branch-rate 0.8503.

## Remaining Non-Blocking Gaps

Some non-expression modules still show uncovered branches in runner, staged execution, pathway evidence, reporting, scoring, and validation utilities. These are not Expression release blockers because the required global gates now pass, but future subsystem passes should continue closing them with behavior-focused tests.
