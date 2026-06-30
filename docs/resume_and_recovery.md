# Resume And Recovery

Resume is fingerprint-based. A stage is reused only when a completed current attempt exists, its
fingerprint matches, all required output files exist, output checksums match, dependency manifests
remain valid, and the stage version is compatible.

Use:

```bash
sirna-offtarget resume --run-dir RUN_DIRECTORY
sirna-offtarget run --config project.yaml --resume
sirna-offtarget run --config project.yaml --from-stage mechanistic_network --resume
```

Old attempts remain available under `attempts/`. Reuse attempts write their own report and
`skipped_reused` manifest without replacing the current successful pointer.

`--no-resume` refuses to target an existing run directory. Without an explicit output directory, it
creates a fresh run directory derived from the configured output name and run id.
