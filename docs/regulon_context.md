# Regulon Context

Regulon overlap is contextual evidence, not pathway enrichment. The staged
pathway contract still keeps legacy `pathway_results` for downstream scoring
compatibility, but regulon-derived fields are also emitted separately as
`regulon_context_results` and `regulon_context_results.tsv`.

New enrichment result collections are:

- `provider_results`
- `locally_calculated_results`
- `consensus_results`

Regulon context must not be interpreted as a statistical pathway enrichment
result.
