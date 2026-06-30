# Pathway Gene Sets

`pathway_enrichment` constructs typed gene sets from `ExpressionAnalysisResultV1`.
The production gene sets are significant upregulated, significant downregulated,
all tested changed, intended-target-related, low-count-excluded, and
unmapped-excluded. Direct, secondary, and mixed candidate sets are not built here
because classification is downstream.

Thresholds are read from `pathway.enrichment.gene_sets` when present:
`adjusted_p_value_threshold`, `absolute_log2_fold_change_threshold`,
`use_shrunken_log2_fold_change`, and `include_low_count`.
