# Identifier Snapshot Ingestion

Identifier snapshots can be built from local user-supplied tabular resources:

```bash
sirna-offtarget identifier-db build \
  --config project.yaml \
  --inputs identifiers.tsv \
  --cache-dir resources/identifier_cache
```

The builder writes provider-neutral normalized files:

- `identifier_entities.tsv`
- `identifier_aliases.tsv`
- `identifier_cross_references.tsv`
- `identifier_deprecated.tsv`
- `identifier_ambiguities.tsv`
- `identifier_snapshot_manifest.json`

The implementation does not fabricate licensed HGNC, Ensembl, UniProt, Entrez,
or Reactome resources. The biological authority of a snapshot depends on the
local input files supplied by the user.
