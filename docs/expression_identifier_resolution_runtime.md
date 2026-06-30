# Expression Identifier Resolution Runtime

The expression stage resolves original gene identifiers through `IdentifierResolverV2`. V2 effect records preserve original ID, detected namespace, canonical gene ID when available, approved symbol, confidence, ambiguity status, organism match, exclusion reason, and warnings.

Unresolved or ambiguous identifiers are not silently promoted to canonical IDs.
