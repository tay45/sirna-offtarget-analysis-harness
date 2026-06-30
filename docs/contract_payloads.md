# Contract Payloads

Core stage contracts use typed Pydantic records rather than unstructured dictionaries.

Typed records include sequence binding sites, gene sequence evidence, expression records, isoform records, pathway records, mechanistic edges and paths, candidate score records, classification records, and visualization artifact records.

Extension metadata is kept explicit and bounded. Core scientific fields remain typed so schema changes can invalidate dependent stages.
