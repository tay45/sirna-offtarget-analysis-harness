# Pathway scientific compliance matrix

| Requirement | Status | Evidence | Remaining limitation |
| --- | --- | --- | --- |
| Explicit provider modes | Implemented | `ProviderSelectionConfig`, `ProviderMode`, loader mode enforcement | Public endpoint catalogs are still user-configured |
| Fetch outside analysis | Implemented | `pathway-db fetch`, analysis rejects `public_fetch` | Live provider-specific auth/rate-limit policies are documented but not exhaustively modeled |
| Snapshot manifests/checksums | Implemented | provider manifests, verification, `.verified` marker | Verification is filesystem-level, not semantic curation review |
| Renormalize without raw re-download | Implemented | `pathway-db renormalize` | Verified marker only if supported schema verifies |
| Central identifier model | Implemented foundation | `sirna_offtarget.identifiers` | No bundled full HGNC/Ensembl/UniProt alias release |
| Entity model | Implemented foundation | `EntityRecord` | Complex membership expansion requires provider data |
| Provider parsers | Partial | Reactome, Panther, OmniPath, SIGNOR, Reactome content/FI adapters | Endpoint-specific production payload variation requires more fixtures |
| Evidence quality | Implemented foundation | component score and levels | Scores are transparent rules, not calibrated probabilities |
| Lineage dedup and consensus | Implemented | consensus edges preserve lineage and support counts | Consensus does not imply mechanistic truth |
| Enrichment provider payload | Implemented foundation | stage payload contains provider results/provenance | Consensus enrichment remains basic aggregation, not a meta-analysis |
| GraphML and topology SVG | Implemented | consensus GraphML and SVG topology renderer | SVG layout is deterministic/simple, not interactive |
| Provider coverage report | Implemented | `provider_coverage.tsv` | Coverage is descriptive only |
| Custom harness preservation | Implemented | staged YAML DAG and contract flow unchanged | None known |

## Deepening Pass Status

| Requirement | Status | Evidence | Remaining limitation |
| --- | --- | --- | --- |
| Production enrichment wiring | partial | `pathway_enrichment` now builds gene sets, background, memberships, local ORA, and consensus payloads | Legacy `PathwayResult` remains for downstream scoring compatibility |
| Provider request builders | correct | `sirna_offtarget.pathway.fetch.*` typed builders | Builders are not yet fully wired into every live fetch adapter |
| Tested background | correct | `BackgroundUniverseV1`, persisted background files | Provider annotation eligibility depends on available cached membership |
| Primary ORA test policy | correct | `calculate_ora_test_values`, `test_primary_test_policy.py` | Only Fisher greater and hypergeometric upper-tail are implemented |
| Multiple-testing family scope | correct | `correction_family_id`, `test_correction_family_scope.py` | Provider-calculated result harmonization remains basic |
| Complete annotation membership guard | correct foundation | `membership_completeness`, `test_complete_annotation_membership.py` | Full Reactome/PANTHER/GO complete membership snapshots still require real supplied data |
| Regulon-context separation | correct foundation | `regulon_context_results.tsv`, `docs/regulon_context.md` | Legacy `pathway_results` remains as deprecated compatibility payload |
| Identifier snapshots | partial but no longer fixture-only | `identifier-db build`, normalized identifier TSVs | Bundled public/licensed HGNC/Ensembl/UniProt retrieval is not included |
| Entity preservation | partial | membership model preserves entity/gene fields | Full Reactome nested traversal is not complete |
| Evidence quality V2 | partial | prior component evidence quality exists | Full V2 component record is not completely wired |
| Lineage V2 | partial | lineage dedup exists | relationship classes are not fully emitted as TSV |
| Consensus V2 | partial | consensus keeps support layers | full V2 record is not complete |
| Path confidence V2 | partial | bottleneck requirement documented | full typed V2 path confidence record not complete |
| Context-aware conflict | partial | conflict limitations documented | context overlap model is not fully implemented |
| Pathway-gene network | correct | bipartite SVG/GraphML renderer and tests | layout is deterministic/static |
| Coverage policy | correct | pyproject and CI use 92%; prior proof was 92.24% | must be rerun after every maturation pass |

## Current Correction Pass Status

| Requirement | Status | Evidence | Remaining limitation |
| --- | --- | --- | --- |
| Remove `min(fisher, hypergeometric)` as primary p-value | Implemented | `local_ora.py`, `enrichment/api.py`, `ora_test_policy.md` | Existing statistical repertoire is limited to the two supported tests |
| Record primary and diagnostic ORA methods | Implemented | `LocalEnrichmentResultV1` fields | Provider-calculated enrichment records are not fully normalized to these fields |
| BH correction by explicit family | Implemented for local ORA | `correction_family_id`, `correction_family_size` | Configurable custom family scopes are documented; current implementation uses the default required scope |
| Reject submitted-hit-only memberships | Implemented for local ORA | hit-only memberships are marked `submitted_hit_only` and excluded by default | Real complete snapshots must be supplied for production enrichment to produce local ORA |
| Identifier resource ingestion | Implemented foundation | `identifier-db build --inputs`, normalized identifier TSVs | No automatic licensed source download |
| Ambiguity preservation | Implemented foundation | `identifier_ambiguities.tsv` | Full provider normalization integration is still partial |
| Reactome nested normalization V2 | Partial | existing provider parser foundation | Full typed nested traversal records are not complete in this pass |
| Evidence/lineage/consensus/path-confidence V2 | Partial | existing foundation and docs | Full requested V2 records are deferred |
| Network visual semantics V2 | Partial | existing mechanistic SVG/GraphML | T-shaped inhibition DOM tests are not fully added in this pass |
| Pathway artifact verification V2 | Partial | policy artifacts and unit tests | Full semantic artifact verifier is deferred |

## Pathway Core V2 Pass Status

| Requirement | Status | Evidence | Remaining limitation |
| --- | --- | --- | --- |
| Complete annotation membership ingestion | Implemented foundation | `annotation-db build/inspect/verify`, `AnnotationMembershipSnapshotV2`, `PathwayMembershipRecordV2` | Real resource authority depends on user-supplied exports |
| Local ORA consumes verified membership snapshots | Implemented foundation | `pathway.enrichment.annotation_cache_dir`, `test_snapshot_backed_local_ora.py` | Synthetic/example config does not bundle production annotation resources |
| PathwayEnrichmentResultV2 | Implemented as artifact | `pathway_enrichment_v2.payload.json`, `PathwayEnrichmentPayloadV2` | Downstream internal migration still uses deprecated V1 compatibility adapter |
| Identifier runtime integration | Partial | identifier snapshot build/verify and summary fields | Provider normalization does not yet fully require `IdentifierResolverV2` |
| BiologicalEntityRecordV2 | Implemented foundation | `sirna_offtarget.pathway.semantics` | Provider adapters still need full migration to emit entity V2 everywhere |
| ProviderEdgeEvidenceRecordV2 | Implemented foundation | `ProviderEdgeEvidenceRecordV2` | Existing provider evidence records are not fully converted |
| EvidenceQualityComponentsV2 | Implemented foundation | deterministic caps and tests | Component calibration is rule-based, not empirically calibrated |
| LineageGroupRecordV2 | Implemented model | `LineageGroupRecordV2` | Full lineage grouping algorithm migration is partial |
| ConsensusMechanisticEdgeRecordV2 | Implemented model | `ConsensusMechanisticEdgeRecordV2` | Existing consensus loader still emits older dict records |
| PathConfidenceRecordV2 | Implemented foundation | bottleneck cap policy and tests | Path tracing does not yet emit V2 confidence for every retained path |
| Context-aware conflict classification | Implemented foundation | `ContextualConflictSummaryV1` and tests | Full candidate-level conflict aggregation is partial |
| Non-color inhibition semantics | Implemented foundation | SVG `inhibition-bar`, GraphML `marker_semantics` tests | Full shape semantics for every entity type are partial |
| Legacy renderer removal | Partial | production visualization uses typed mechanistic/pathway-gene renderers | legacy report compatibility helpers remain accessible |
| Provider version extraction | Partial | provider manifests record version confidence | provider-specific live metadata extractors remain incomplete |
| Verification V3 | Partial | annotation snapshot verify, marker semantics, policy tests | full cross-artifact semantic verifier is not complete |

The pathway layer is materially more auditable after this pass, but it should not be described as
fully scientifically mature. Remaining work includes broad official endpoint fixture coverage,
licensed identifier snapshot ingestion, complex expansion, and calibrated evidence confidence.
