# Annotation Membership Snapshots

Annotation membership snapshots are offline, verified resources used by local
ORA. They are built from user-supplied Reactome, PANTHER, or GO membership
exports rather than from provider enrichment hits.

Build:

```bash
sirna-offtarget annotation-db build \
  --config project.yaml \
  --provider reactome \
  --annotation-source REACTOME_PATHWAY \
  --inputs reactome_memberships.tsv \
  --cache-dir resources/annotation_cache
```

Inspect and verify:

```bash
sirna-offtarget annotation-db inspect --cache-dir resources/annotation_cache
sirna-offtarget annotation-db verify --cache-dir resources/annotation_cache
```

The normalized snapshot contains `annotation_memberships.tsv`,
`annotation_membership_manifest.json`, `annotation_membership_coverage.tsv`,
and `incomplete_annotation_terms.tsv`.
