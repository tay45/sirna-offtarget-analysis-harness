# Stage Manifests

Each stage attempt writes `stage_manifest.json` with run id, stage name, stage version, attempt
number, status, timing, software version, Python/platform metadata, original/resolved/relevant
configuration hashes, stage fingerprint, direct input artifacts, dependency manifest hashes,
dependency output hashes, output artifacts, output checksums, output schema versions, reports,
offline status, and reproducibility metadata.

Supported statuses include `pending`, `running`, `completed`, `completed_with_warnings`, `failed`,
`interrupted`, `blocked`, `invalidated`, and `skipped_reused`.
