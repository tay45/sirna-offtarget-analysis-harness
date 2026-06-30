# Identifier resolution

Identifier handling is centralized in `sirna_offtarget.identifiers`. It detects HGNC symbols,
Ensembl gene/transcript IDs, Entrez IDs, UniProt accessions, Reactome stable IDs, SIGNOR entity IDs,
and coarse complex/family/entity-set identifiers.

Normalization is type-aware. HGNC symbols and provider stable IDs are uppercased, while Ensembl
version suffixes are removed without changing the core identifier. Deprecated aliases are only
mapped through explicit alias tables; ambiguous aliases remain auditable and are not silently
collapsed.

Entity records capture canonical identifier, display name, entity type, organism, source
identifiers, mapping confidence, provenance, and warnings.
