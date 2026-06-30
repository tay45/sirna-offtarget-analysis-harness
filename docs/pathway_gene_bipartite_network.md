# Pathway-Gene Bipartite Network

`network_visualization` writes a real pathway-gene bipartite SVG and GraphML.
Pathway nodes contain provider/source, pathway ID/name, FDR, fold enrichment,
and gene-set category. Gene nodes contain gene symbol and expression metadata
when available. Edges represent matched membership in the enriched result.

This graph is enrichment context only. It is not causal pathway evidence.
