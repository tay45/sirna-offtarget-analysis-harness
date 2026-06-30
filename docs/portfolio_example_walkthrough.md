# Portfolio Example Walkthrough

Run:

```bash
sirna-offtarget run \
  --config examples/portfolio/config.yaml \
  --until-stage transcript_targetability_ratio
```

Then open:

`examples/portfolio/portfolio_result_summary.md`

The example includes:

- a single-transcript gene with cleavage-compatible evidence,
- a multi-transcript gene where only a subset is targetable,
- a seed-only gene,
- an evaluated non-targetable gene,
- a gene with unavailable sequence evidence.

The run produces ratio artifacts only as the public interpretation boundary.
Final classification remains planned.
