# Next Stage: Short-Read Isoform Boundary

Date: 2026-06-26

The next recommended subsystem pass is the short-read isoform boundary.

## Starting Point

Use committed Expression V2 outputs only:

- `ExpressionAnalysisResultV2`
- `normalized_gene_effects_v2.jsonl`
- `IsoformGeneEffectInputV1`

## Boundary Rules

- Do not load Expression V1 normalized effects.
- Do not re-enable the legacy precomputed `ExpressionResult` backend.
- Do not infer missing condition means, adjusted p-values, replicate consistency, or shrinkage.
- Keep the existing isoform scientific algorithm unchanged unless the pass explicitly scopes a scientifically reviewed replacement.

## Suggested First Checks

- Verify every isoform-stage expression input is traceable to a committed V2 record id.
- Separate expression-input correctness from isoform-inference scientific assumptions.
- Add explicit tests for short-read ambiguity, transcript-level identifiability limits, and cases where isoform inference must remain indeterminate.
