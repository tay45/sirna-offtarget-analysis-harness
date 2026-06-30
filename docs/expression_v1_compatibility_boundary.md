# Expression V1 Compatibility Boundary

Expression V1 compatibility is noncanonical. It is generated only from V2
records and is marked deprecated and loss-aware in
`expression_analysis_result_v1_compatibility.json`.

Nullable V2 fields are not filled with fabricated V1 values. Rows that cannot be
represented without inventing required V1 fields are omitted from the V1 view and
recorded in `loss_rows`.
