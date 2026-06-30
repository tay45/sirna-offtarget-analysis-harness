# Expression Downstream Consumer Inventory

This inventory records current production and verification consumers that read
expression effects after the Expression V2 boundary. The scientific source of
truth is:

`ExpressionAnalysisResultV2` -> `normalized_gene_effects_v2.jsonl` ->
typed read-only downstream views.

Production downstream stages must not parse the original expression source
table, load `ExpressionAnalysisResultV1`, or load
`normalized_gene_effects_v1.jsonl`.

| Stage or module | Current loader | Current contract or artifact used | Fields read | Nullable values | Uses V1 | Invents values | Drops records | Replacement V2-derived view | Migration status |
|---|---|---|---|---|---:|---:|---:|---|---|
| Isoform uncertainty | `load_isoform_gene_effect_inputs` | committed `ExpressionAnalysisResultV2`, committed `normalized_gene_effects_v2.jsonl` | source V2 record ID, original/canonical gene IDs, approved symbol, contrast, canonical log2 fold change, effect source, direction, tested/filter/low-count/model/statistical-support states, adjusted p-value/status, optional abundance summaries, warnings | adjusted p-value, abundance summaries, replicate consistency, shrunken fold change | No | No | Only missing canonical gene/effect, ambiguous identifier, model failure, unsupported state | `IsoformGeneEffectInputV1` | Complete |
| Pathway evidence architecture | `load_pathway_gene_effect_inputs` | committed `ExpressionAnalysisResultV2`, committed `normalized_gene_effects_v2.jsonl` | canonical gene key, canonical log2 fold change, direction, low-count state, adjusted p-value/status, source V2 record ID | adjusted p-value and abundance are not required | No | No | Only shared base exclusion reasons | `PathwayGeneEffectInputV1` | Complete |
| Mechanistic evidence architecture | `load_network_gene_effect_inputs` | committed `ExpressionAnalysisResultV2`, committed `normalized_gene_effects_v2.jsonl` | gene key, numerical direction, tested/filter/model states, source V2 record ID | adjusted p-value and abundance are not required | No | No | Only shared base exclusion reasons | `NetworkGeneEffectInputV1` | Complete |
| Verification and tests | committed V2 loaders and view builders | committed stage manifest and output artifact records | manifest status, checksums, schema, source V2 record ID, inclusion/exclusion counts | Null preservation is asserted | No | No | Exclusions require reasons | shared and consumer-specific view tests | Complete |
| Historical V1 normalized-effect helper | `load_committed_normalized_gene_effects` | none in production | none | Not applicable | Rejected | No | Not applicable | raises `LegacyExpressionArtifactNotSupportedError` | Disabled |

## Inclusion Policy

The shared default inclusion policy includes a V2 record for downstream
annotation when the canonical gene ID and canonical effect are available, the
identifier is not explicitly ambiguous, and the model/filter state is compatible
with downstream annotation.

The following do not exclude an otherwise usable record: missing adjusted
p-value, missing condition summaries, unavailable replicate consistency, and
absence of shrinkage.
