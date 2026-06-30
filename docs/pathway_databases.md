# Pathway Databases

Reactome Analysis Service is used for enrichment. PANTHER is used for
functional/pathway enrichment and cross-checking. OmniPath is the primary
signed/directed mechanistic graph. SIGNOR provides high-confidence causal
support. Reactome Content Service provides curated pathway/reaction context.
Reactome FI provides broad functional connectivity and module support.

Cached database snapshots are required for reproducibility.

Analysis commands read only local cache files. Network access is restricted to
the explicit `sirna-offtarget pathway-db fetch` command.

Cached provider adapters accept TSV, CSV, JSON, or JSONL snapshots named after
the provider, for example `omnipath.tsv`, `signor.tsv`, `reactome_fi.tsv`,
`reactome_content.tsv`, `panther.tsv`, or `reactome_analysis.tsv`. The parser
validates the minimal required columns:

- OmniPath and SIGNOR: `source`, `target`, `sign`
- Reactome FI and Pathway Commons: `source`, `target`
- Reactome Content: `source`, `target`, `pathway_id`
- Reactome Analysis and PANTHER: `gene`, `pathway_id`, `pathway_name`
