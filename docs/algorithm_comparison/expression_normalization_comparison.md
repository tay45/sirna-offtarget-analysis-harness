# Expression Normalization Comparison

Date: 2026-06-24

## Scope

This comparison covers only expression input normalization and gene-level normalized effect records. It does not change isoform allocation, mechanistic pathway analysis, expected direct-effect logic, residual-effect logic, direct/secondary scoring, integration, or final classification.

## Compared Inputs

| Input type | Supported role | Key constraint |
| --- | --- | --- |
| Raw integer counts | Count-model differential expression through an explicit backend | Counts must be unnormalized sample-level observations with sample metadata and a declared contrast. |
| Precomputed differential-expression table | Import of externally normalized and tested gene-level effects | The harness validates and preserves supplied effect columns; it does not rerun normalization or testing. |
| Normalized expression matrix | Descriptive expression summaries only | The harness does not infer count-model p-values from normalized values. |
| TPM, FPKM, RPKM | Descriptive abundance only when explicitly declared | These scales are not accepted as raw-count input for DESeq2-like count-model inference. |

## Source Rationale

DESeq2's official vignette states that its statistical workflow starts from un-normalized counts and that transformed or normalized values should not be supplied as model input. It models count data with negative-binomial GLMs and internally corrects for library size. Source: https://bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html

edgeR is also a count-based differential-expression framework for sequencing count data and normalization factors. Source: https://bioconductor.org/packages/release/bioc/vignettes/edgeR/inst/doc/edgeRUsersGuide.pdf

limma-voom supports precision-weighted modeling of transformed RNA-seq count data after an explicit voom transformation rather than treating arbitrary normalized values as raw counts. Source: https://bioconductor.org/packages/release/bioc/vignettes/limma/inst/doc/usersguide.pdf

## Decision Criteria

The selected interface must preserve provenance, separate tested from untested/filtered states, keep effect direction distinct from significance, and expose a read-only normalized-effect artifact for downstream stages. It must not make unsupported statistical claims from TPM/FPKM/RPKM or user-normalized matrices.
