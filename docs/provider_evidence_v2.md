# Provider Evidence V2

`ProviderEdgeEvidenceRecordV2` records directedness, sign, relation type,
mechanism, directness, functional/contextual flags, source provider, original
database, references, context, prediction status, identifier snapshot, provider
snapshot, provider version, and normalization version.

The model is a foundation for provider normalization migration. Existing
provider adapters still need full conversion to emit this record everywhere.
