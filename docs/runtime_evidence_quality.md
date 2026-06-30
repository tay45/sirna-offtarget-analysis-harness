# Runtime Evidence Quality

Runtime evidence quality is calculated from evidence metadata, lineage context, mapping confidence, organism comparison, publication/database support, prediction status, directness, and missing context fields.

Sign contributes to quality but is not the only input. Missing context is recorded in `missing_components`; absent publications and low mapping confidence trigger caps.

The current policy version is `runtime-evidence-quality-v2`.
