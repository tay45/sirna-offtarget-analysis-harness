# Entity Model V2

`BiologicalEntityRecordV2` distinguishes genes, proteins, transcripts,
complexes, protein families, entity sets, pathways, reactions, small molecules,
phenotypes, and unknown entities.

Rules enforced in the model include:

- small molecules, phenotypes, and unknown entities cannot carry canonical gene IDs
- complexes and families remain typed entities
- transcripts are not genes unless a later analysis policy explicitly collapses them
- entity expansion must be explicit and auditable
