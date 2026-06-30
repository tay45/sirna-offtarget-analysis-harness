# Identifier Ambiguity

Ambiguous identifier mappings are preserved in `identifier_ambiguities.tsv`.
The snapshot builder does not select the first candidate mapping arbitrarily.

Current production posture is conservative:

- unambiguous mappings may enter canonical cross-reference files
- one-to-many mappings remain auditable
- ambiguous IDs are visible in manifest counts
- downstream full provider normalization integration is still partial
