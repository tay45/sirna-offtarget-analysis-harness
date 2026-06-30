# Expression Execution Support Matrix

Date: 2026-06-24

| Mode/backend | Validation | Execution | Production | Inferential statistics | Descriptive effect | Required backend | Bundled/external | Failure behavior |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `precomputed_de` / `precomputed` | yes | yes | yes, as trusted import | imported only | yes | `precomputed` | external results imported | fails on schema/value errors |
| `raw_counts` / `synthetic_demo` | yes | yes | no | no | yes | `synthetic_demo` | bundled demo | emits demonstration-only warning |
| `raw_counts` / `pydeseq2` | yes | no | no | no | no | unavailable adapter | external unavailable | `raw_count_production_backend_unavailable` |
| `raw_counts` / `deseq2_r` | yes | no | no | no | no | unavailable adapter | external unavailable | `raw_count_production_backend_unavailable` |
| `normalized_matrix` | yes | no | no | no | no | not implemented | none | `normalized_matrix_execution_not_supported` |

The harness must not claim production raw-count differential expression while bundled raw-count production adapters raise unavailable/not-implemented errors. Normalized-matrix execution is validation-only in this pass.
