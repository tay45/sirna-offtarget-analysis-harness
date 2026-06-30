# Dependency Types

Stages declare two dependency classes.

`data_dependencies` are upstream contracts whose payload fields or artifacts are consumed by the downstream stage. Their contract and artifact hashes participate in the downstream scientific fingerprint.

`completion_dependencies` are ordering dependencies only. They must be complete before the downstream stage runs, but their scientific payload is not loaded as input.

Unused data dependencies are prohibited. Completed stage manifests include declared data dependencies, completion dependencies, and explicit consumption records.
