# Portfolio Example

This deterministic synthetic example demonstrates the current validated workflow
through `transcript_targetability_ratio`. It does not run final direct,
secondary, mixed, or unresolved classification.

Run from the repository root:

```bash
sirna-offtarget run \
  --config examples/portfolio/config.yaml \
  --until-stage transcript_targetability_ratio
```

Outputs are written under `examples/portfolio/output/`. The first file to inspect
is the committed ratio table:

`examples/portfolio/output/stages/08_transcript_targetability_ratio/attempts/attempt_001/committed/outputs/gene_transcript_targetability_ratios_v1.tsv`

Seed-only evidence is preserved in `seed_only_transcript_ids` and
`seed_only_transcript_count`. Unresolved sequence evidence is preserved in
`transcript_targetability_ratio_unresolved_v1.tsv`; it is not converted to
non-targetable evidence.

The curated public summary is:

`examples/portfolio/portfolio_result_summary.md`
