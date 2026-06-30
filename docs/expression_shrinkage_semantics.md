# Expression Shrinkage Semantics

Imported shrunken log2 fold change is preserved only when a shrunken value is present. Missing row-level shrinkage remains null in `NormalizedGeneEffectRecordV2`.

The canonical effect may fall back to reported unshrunken log2FC, but `canonical_effect_source` must then be `reported_unshrunken_log2fc`. The harness must not copy unshrunken log2FC into the shrunken field.
