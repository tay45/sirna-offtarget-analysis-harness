# Stage Execution

The execution package runs a versioned stage DAG around the existing scientific APIs. Each stage
declares dependencies, relevant configuration paths, direct input files, an implementation version,
and a typed output contract.

Stages execute inside `stages/NN_stage_name/attempts/attempt_###`. A successful attempt writes
`stage_manifest.json`, `status.json`, `report.json`, `report.html`, logs, inputs, outputs, and
checksums before updating `current.json`. Failed attempts are preserved and never promoted as valid
upstream inputs.

No downstream stage calls the full workflow orchestrator. Downstream stages consume typed dependency
contracts from `committed/outputs/stage_result.json`.
