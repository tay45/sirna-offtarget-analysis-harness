# Provider modes

Provider access is explicit and auditable. The top-level `providers` map accepts one entry per
provider with `mode`, `required`, `snapshot_id`, `endpoint`, `timeout_seconds`, `retry_count`, and
`expected_content_type`.

Supported modes:

- `public_fetch`: only valid for the `pathway-db fetch` command. It reads a configured endpoint,
  validates status/content/non-empty response, writes raw and normalized files, and records a
  manifest.
- `public_cache`: valid during analysis. It requires a verified immutable cache snapshot; required
  providers fail fast when missing.
- `local_snapshot`: uses local recorded resources or local cache snapshots.
- `synthetic_fixture`: reserved for synthetic tests and examples.
- `disabled`: provider is intentionally skipped.

Normal analysis stages do not perform network access. A `public_fetch` provider found during
analysis is rejected; fetch must be run explicitly before analysis.
