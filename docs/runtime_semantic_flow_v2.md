# Runtime Semantic Flow V2

The mechanistic runtime now routes normalized edge rows through a centralized V2 builder before committing `MechanisticNetworkResultV2`.

Current flow:

1. provider/local normalized edge rows
2. runtime identifier resolution records
3. `BiologicalEntityRegistryV2`
4. `ProviderEdgeEvidenceRecordV2`
5. lineage grouping
6. runtime evidence-quality records
7. consensus edge construction
8. semantic graph-layer construction
9. signed and unsigned path partitioning
10. path-confidence records
11. contextual conflict records
12. V2-only reporting

The old `runtime_symbol_view` placeholder is no longer emitted. When no verified identifier snapshot is configured, records are marked as symbol-only runtime resolution with reduced mapping confidence and explicit warnings.
