# Network Visualization

The reporting layer emits deterministic SVG, PNG fallback, and GraphML outputs.
Reporting consumes finalized typed network results and does not perform pathway
inference, path search, scoring, or scientific calculations.

The visualization stage also writes the finalized normalized network payloads:

- `normalized_mechanistic_edges.tsv`
- `normalized_mechanistic_paths.tsv`
- `normalized_mechanistic_network.json`
