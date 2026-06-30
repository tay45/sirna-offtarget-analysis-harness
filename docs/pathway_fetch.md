# Pathway Fetch

Fetch is explicit:

```bash
sirna-offtarget pathway-db fetch --config project.yaml \
  --providers reactome,panther,omnipath,signor,reactome-fi \
  --cache-dir resources/pathway_cache
```

The command records raw responses and normalized records. Provider failure is
reported instead of silently substituting synthetic data. Runtime stages read
only cached snapshots or explicitly configured local snapshots.

