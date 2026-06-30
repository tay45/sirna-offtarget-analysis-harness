# YAML Configuration

YAML is the canonical user-facing configuration format. The standard entry point is:

```bash
sirna-offtarget run --config project.yaml
```

The loader preserves `run_config.original.yaml` unchanged and writes `run_config.resolved.yaml`
with defaults, resolved paths, execution policy, and CLI operational overrides.

Top-level sections are versioned by `schema_version` and include `project`, `inputs`, `sirna`,
`experiment`, `sequence`, `expression`, `isoform`, `pathway`, `scoring`, `reporting`,
`execution`, and `outputs`. Existing scientific settings should live in YAML, while CLI flags are
reserved for operational controls such as `--output-dir`, `--resume`, `--from-stage`,
`--until-stage`, `--force-stage`, `--force-downstream`, `--offline`, `--dry-run`, and `--run-id`.
