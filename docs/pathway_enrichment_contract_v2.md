# Pathway Enrichment Contract V2

The pathway stage now writes `pathway_enrichment_v2.payload.json` under the
committed pathway enrichment outputs. Its top-level sections are:

- `gene_sets`
- `background_universe`
- `provider_calculated_enrichment`
- `locally_calculated_enrichment`
- `enrichment_consensus`
- `annotation_membership_summary`
- `identifier_mapping_summary`
- `provider_snapshot_manifest`
- `annotation_snapshot_manifest`
- `regulon_context`
- `warnings`

The legacy V1 contract is retained as a deprecated compatibility payload for
downstream scoring code that has not yet migrated.
