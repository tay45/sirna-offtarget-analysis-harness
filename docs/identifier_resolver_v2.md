# Identifier Resolver V2

`IdentifierResolverV2` loads a verified identifier snapshot directory and builds indexes for approved symbols, aliases, previous symbols, and cross-reference records present in `records.jsonl`.

Resolution returns `IdentifierResolutionRecordV2`. Unresolved and ambiguous identifiers are not represented as mapped genes. With the default ambiguity policy, ambiguous identifiers are excluded and retain candidate mappings for audit.

Runtime provider normalization should pass raw provider identifiers through this resolver before creating canonical biological entities.
