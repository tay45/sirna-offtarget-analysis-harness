# Dependency DAG

The current executable DAG is explicit and cycle-checked:

`validate -> prepare_inputs -> map_identifiers`, with sequence and expression
branches feeding isoform uncertainty, transcript targetability, and the terminal
expected direct-effect evidence stage.

The official stage order is:

1. `validate`
2. `prepare_inputs`
3. `map_identifiers`
4. `sequence_analysis`
5. `expression_analysis`
6. `isoform_uncertainty`
7. `transcript_targetability`
8. `transcript_targetability_ratio`
9. `expected_direct_effect`

The runner topologically sorts this graph, rejects circular dependencies, and
blocks a stage when required upstream manifests are missing or invalid.
