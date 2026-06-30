# Output Ownership

Network outputs have a single production owner: `write_v2_reports`.

Owned outputs:

- `network_summary.svg`
- `network_summary.graphml`
- `pathway_gene_network.svg`
- `pathway_gene_network.graphml`
- `candidate_networks/*.svg`
- `candidate_networks/*.graphml`

The runtime writes `output_ownership_report.json` to document the owner map and duplicate-output status.
