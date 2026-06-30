# Expression Missing Padj Policy

Row-level missing adjusted p-values are allowed for precomputed imports. Missing values are represented as `adjusted_pvalue_unavailable`, `independent_filtered`, `outlier_filtered`, `model_not_estimable`, or `model_failure` when imported status columns provide that explanation.

Missing adjusted p-values are never converted to zero, one, significant, or not significant in V2 canonical records.
