# Expression Normalization Limitations

Date: 2026-06-24

## Scientific Limits

This pass records normalization and gene-level effect provenance; it does not make a new biological attribution claim. A normalized-expression effect is not evidence of direct siRNA binding, isoform-level targeting, pathway causality, or final off-target classification.

Low-count and untested genes are represented as explicit states. They must not be silently treated as nonsignificant tested genes. Missing adjusted p-values are represented as unavailable rather than significant or nonsignificant.

## Operational Limits

The built-in synthetic backend remains demonstration-only. It produces deterministic normalized summaries and heuristic effect scores for local testing, not production statistical p-values.

The precomputed table path assumes the external caller has already performed normalization, model fitting, shrinkage, and multiple-testing correction. The harness validates ranges, identifiers, and declared scales, but it does not audit the external statistical workflow.

The normalized-matrix mode is intentionally narrow. It supports declared provenance and descriptive values, but this pass does not add a production statistical model over arbitrary normalized expression matrices.
