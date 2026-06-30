# Runtime Path Confidence

Path confidence records are calculated from retained path edge IDs and runtime evidence-quality scores.

The final capped score is constrained by:

- average edge quality
- minimum edge quality bottleneck
- minimum mapping-confidence cap

Each retained path records its bottleneck edge, graph-layer path type, completeness flags, conflict count, missing-context fraction, and policy version.
