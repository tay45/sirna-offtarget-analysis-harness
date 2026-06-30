# Failure Provenance

A failed or interrupted attempt is preserved in its attempt directory. The runner writes
`status.json`, `error.json`, `traceback.txt`, `command.txt`, `environment.json`,
`resolved_stage_config.yaml`, `input_manifest.json`, `dependency_manifest.json`, `logs/stage.log`,
`logs/events.jsonl`, `partial_outputs/`, `failure_report.html`, and `failure_report.json`.

`error.json` records the exception class, message, failure category, failed operation, stage,
attempt number, timestamp, recoverability, suggested retry command, upstream dependency state,
provider/backend context, and exit code when available.
