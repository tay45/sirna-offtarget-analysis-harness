# Stage Contracts

Every committed stage writes `committed/outputs/stage_result.json`. The file is a Pydantic-validated
contract containing contract name, schema version, stage name, stage version, run id, attempt number,
software version, typed payload, artifact references, warnings, and provenance.

Downstream stages load dependencies through the shared contract loader. The loader validates current
attempt status, contract name, schema version, artifact existence, artifact checksum, and manifest
consistency before returning typed data.
