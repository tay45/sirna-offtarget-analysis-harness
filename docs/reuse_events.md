# Reuse Events

Execution attempts represent actual stage execution only.

When a completed stage is reused, the runner writes `stages/<stage>/reuse_events.jsonl`. Reuse events include timestamp, reused attempt number, fingerprint, verification result, dependency status, config revision, and reason.

Unchanged resume does not create new attempt directories.
