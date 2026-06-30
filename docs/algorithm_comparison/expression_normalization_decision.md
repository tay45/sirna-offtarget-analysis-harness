# Expression Normalization Decision

Date: 2026-06-24

## Decision

The harness will support three explicit expression input modes:

1. `raw_counts`: sample-by-gene integer counts consumed only by an explicit backend.
2. `precomputed_de`: externally generated differential-expression results imported as gene-level effects.
3. `normalized_matrix`: declared normalized expression values for descriptive summaries only.

The committed output for expression analysis will include a separate normalized-effect artifact in addition to the existing `ExpressionAnalysisResultV1` compatibility contract. Downstream stages may consume this artifact through a read-only loader, but this pass does not rewire isoform, mechanistic, scoring, integration, or classification behavior.

## Normalized-Effect Contract

Each gene-level normalized-effect record includes:

- gene identifier and namespace
- organism and contrast identifier
- canonical log2 fold-change effect and effect scale
- raw and adjusted p-values when available
- tested state and low-count state
- significance state separate from direction
- normalization run identifier and method provenance
- backend name/version and demonstration flag

Direction is derived from the committed canonical effect value. Significance is derived only from a valid adjusted p-value and configured threshold. A negative nonsignificant log2 fold change remains a decreased effect with `not_significant` status; it is not relabeled as unchanged by significance alone.

## Unsupported Claims

The harness will not infer count-model p-values from TPM, FPKM, RPKM, VST, rlog, log-CPM, or other normalized values. Those scales can be accepted only when the user explicitly declares a descriptive input mode or supplies a precomputed differential-expression table with provenance.
