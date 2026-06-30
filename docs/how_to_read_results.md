# How to Read Results

Start with the ratio table:

`gene_transcript_targetability_ratios_v1.tsv`

Important columns:

- `n_total_eligible_transcripts`: formal N.
- `m_targetable_transcripts`: formal M when definitive.
- `ratio_m_over_n`: equal-prior targetable transcript fraction.
- `seed_only_transcript_count`: transcripts with seed-only evidence preserved separately.
- `unresolved_transcript_count`: transcripts whose evidence is unavailable.
- `ratio_status`: whether the M/N ratio is definitive or unavailable.

Missing sequence is not treated as proof that a transcript is non-targetable.
Seed-only evidence is preserved but excluded from default cleavage-compatible M.
