# Expression V2 Canonical Flow

Precomputed differential-expression input is imported through
`import_precomputed_expression_v2`. Production import no longer runs the
precomputed table through the legacy V1 backend and then reconstructs V2.

The canonical artifacts are `expression_analysis_result_v2.json`,
`expression_normalization_run_v2.json`, `expression_contrasts_v2.json`, and
`normalized_gene_effects_v2.jsonl`. V1 output is retained only as a deprecated
compatibility view.
