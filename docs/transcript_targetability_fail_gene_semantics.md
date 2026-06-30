# Transcript Targetability Fail-Gene Semantics

`MissingTranscriptSequencePolicyV1.mode = fail_gene` is gene-level behavior.
When any eligible transcript in a gene lacks a required transcript sequence, the
entire gene is failed for transcript targetability.

Failed genes produce `transcript_targetability_gene_failures_v1.jsonl` records
and per-transcript evidence with `not_evaluated_due_to_gene_failure`. No
canonical sites or best-site records are retained for the failed gene. Other
genes continue normally.

Summary counts distinguish genes examined, genes successfully evaluated, genes
failed under fail-gene, evaluated transcripts, unavailable transcripts,
transcripts not evaluated due to gene failure, and canonical sites discarded due
to gene failure. This stage still does not calculate formal M.
