# Identifier Snapshots

`sirna-offtarget identifier-db fetch/inspect/verify` manages offline identifier
snapshots. Normal analysis remains offline. The current bundled writer creates a
fixture snapshot with HGNC, UniProt, deprecated-symbol, and ambiguity examples;
production deployments should replace it with licensed HGNC, Ensembl, Entrez,
UniProt, and Reactome reference resources.

Ambiguous one-to-many mappings remain ambiguous and are not silently resolved.
