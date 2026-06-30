# Mechanistic Network Result V2

`MechanisticNetworkResultV2` is the canonical committed contract for the mechanistic network stage.

Required sections include biological entities, identifier resolution records, provider evidence, lineage groups, consensus edges, graph-layer summary, signed paths, unsigned context paths, path confidence records, contextual conflicts, unsupported entities, provider and identifier snapshot manifests, warnings, coverage summary, and scientific policy manifest.

The current runtime populates these sections from normalized mechanistic edges and retained paths. The contract no longer commits V1 `pathway_results`, `edges`, or `paths` as the canonical mechanistic artifact.
