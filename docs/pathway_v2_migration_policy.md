# Pathway V2 Migration Policy

V2 pathway contracts are canonical for runtime storage, validation, downstream loading, and reporting.

Canonical runtime contracts:

- `PathwayEnrichmentResultV2`, schema version `2`
- `MechanisticNetworkResultV2`, schema version `2`

Deprecated contracts:

- `PathwayEnrichmentResultV1`
- `MechanisticNetworkResultV1`

V1 contracts may remain in the package only for explicit compatibility adapters and old artifact inspection. The normal staged DAG must not load V1 pathway or mechanistic contracts after this migration. A V1 artifact in a V2 production run is rejected by contract validation because the stage registry now expects the V2 contract name and schema version.

Compatibility direction is V2 to V1 only. The adapter in `sirna_offtarget.contracts.adapters.pathway_v2_to_v1` emits a deprecation warning and does not fabricate unrecoverable V1 pathway result fields. Regulon context remains separate context and is not converted into enrichment evidence.

Sunset policy: V1 adapters are adapter-only, excluded from stage declarations, and must not be imported by production execution modules.
