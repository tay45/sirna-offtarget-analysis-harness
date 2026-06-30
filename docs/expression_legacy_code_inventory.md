# Expression Legacy Code Inventory

Date: 2026-06-26

## Disabled Or Isolated Paths

- `PrecomputedDifferentialExpressionBackend.run` is disabled and raises `LegacyExpressionPathNotSupportedError`.
- `load_committed_normalized_gene_effects` is a legacy V1 loader and raises `LegacyExpressionArtifactNotSupportedError`.
- `ExpressionAnalysisResultV1` is not accepted as a production downstream dependency.
- V1 normalized gene effects are not a scientific source of truth for isoform,
  pathway, network, or current transcript targetability consumers.

## Supported Paths

- `ExpressionAnalysisResultV2` is the committed Expression contract.
- `normalized_gene_effects_v2.jsonl` is the committed normalized effect artifact.
- `import_precomputed_expression_v2` remains the supported precomputed differential-expression import path.
- Typed downstream input views are generated from committed V2 records.

## Removed Dangerous Behavior

The legacy precomputed `ExpressionResult` backend previously could derive or default scientific fields that should be explicit upstream evidence:

- adjusted p-value defaulting,
- condition-specific expression means copied or inferred from aggregate abundance,
- replicate consistency defaulting,
- shrunken fold change copied from reported unshrunken fold change.

This pass prevents that executable legacy path from producing production `ExpressionResult` records.
