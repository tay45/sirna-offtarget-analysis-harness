# Entity Registry Runtime

`BiologicalEntityRegistryV2` owns biological entity creation for the mechanistic V2 payload. It deduplicates deterministic entity IDs, preserves non-gene entity types, tracks unsupported unknown entities, and serializes registry rows into `MechanisticNetworkResultV2`.

The registry exposes registration methods for genes, proteins, transcripts, complexes, families, entity sets, pathways, reactions, small molecules, phenotypes, and unknown provider entities.

Expansion is routed through `expand_for_policy`; `no_expansion` is the default safe behavior.
