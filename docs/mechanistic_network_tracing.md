# Mechanistic Network Tracing

Signed paths require explicit directed signed edges. Path signs compose across
all edges: activation is `+1`, inhibition is `-1`, and the composed path sign is
the product. Unknown or unsigned edges are not treated as positive.

Conflicting signed paths are reported instead of collapsed into a single claim.

The `mechanistic_network` contract emits normalized edges and paths. Edge records
preserve provider, sign, directionality, references, database version, retrieval
snapshot, lineage key, predicted-only status, and conflict flags. Path records
preserve ordered nodes, ordered edge ids, composed sign, expected direction after
target decrease, observed direction, direction consistency, provider sources,
reference ids, evidence score, unsigned edge count, and conflict status.

Secondary scoring penalizes contradictory and conflicting paths and gives only
limited support to unsigned paths. Reactome FI-style unsigned support can support
context or module membership, but it cannot create a directional causal claim.
