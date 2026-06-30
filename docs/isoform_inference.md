# Isoform Inference

For each gene, eligible transcripts are counted after sequence availability and
duplicate transcript checks. `M` is the number of distinct eligible transcripts
containing at least one relevant siRNA site and `N` is the number of eligible
transcripts. The equal-transcript prior is `M / N`.

Back-calculation reports assumption-based inferred targeted-transcript
contribution, not measured transcript abundance.
