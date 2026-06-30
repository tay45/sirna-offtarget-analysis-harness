# Expression Backends

Supported backend interfaces include precomputed differential-expression tables,
optional PyDESeq2, optional R/DESeq2, and a synthetic demonstration backend.

The synthetic backend is marked `demonstration_only=true`. Its synthetic effect
quantity is not a statistical p-value and must not be interpreted as calibrated
RNA-seq significance.

`expression.backend` is required. The harness does not silently fall back to a
synthetic backend when a production backend is missing.

```yaml
expression:
  backend: precomputed
  precomputed_table: deseq2_results.tsv
  gene_column: gene
  base_mean_column: baseMean
  log2_fold_change_column: log2FoldChange
  shrunken_log2_fold_change_column: lfcShrink
  standard_error_column: lfcSE
  p_value_column: pvalue
  adjusted_p_value_column: padj
  design_formula: "~ condition"
```

`backend: pydeseq2` and `backend: deseq2_r` are explicit routes only; this
build raises a clear error unless the local adapter is provided. Use
`backend: synthetic` only for software validation fixtures.
