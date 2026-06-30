# Provider snapshot immutability

Each provider snapshot stores raw files, normalized JSONL, a provider manifest, file checksums, and
a `.verified` marker. Verification checks manifest schema, duplicate snapshot IDs, missing files,
checksums, incomplete snapshots, organism consistency, and stale temporary files.

`pathway-db renormalize` creates a new snapshot from existing raw data without re-downloading. The
new snapshot is marked verified only when the full cache verifies under the supported schema.

Snapshot identity includes provider, organism, raw payload digest, and cache schema. This avoids
quietly overwriting older snapshots when parsing or normalization logic changes.
