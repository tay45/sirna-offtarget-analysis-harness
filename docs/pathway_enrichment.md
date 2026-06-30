# Pathway Enrichment

Upregulated and downregulated genes are analyzed separately. The tested
detectable expression universe is the preferred enrichment background.
Enrichment does not prove secondary causality.

The `pathway_enrichment` stage is intentionally context-only: it consumes
expression results and regulon annotations, and it does not traverse mechanistic
graphs or infer target-to-candidate causality. Candidate secondary scoring uses
the finalized `mechanistic_network` result for causal path support, while
enrichment remains a supporting context and reporting artifact.
