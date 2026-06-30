# Expression Precomputed Import Semantics

Precomputed differential-expression rows are imported scientific results. The harness validates ranges and preserves row-level values; it does not rerun normalization, reconstruct condition means from `baseMean`, or infer missing method provenance.

When condition-specific summaries are absent, V2 records keep `control_abundance_summary` and `treatment_abundance_summary` as null and add a warning. `baseMean` is retained only as `mean_abundance_summary`.
