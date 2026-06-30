# Expression Missing Effect Policy

Expression V2 preserves missing row-level effect, adjusted p-value, and
shrinkage values as null. Missing `log2FoldChange` produces
`canonical_log2_fold_change=null` and `canonical_effect_source=unavailable`.

The importer does not copy reported effects into shrinkage fields, does not
replace missing p-values with 1, and does not replace missing effects with 0.
