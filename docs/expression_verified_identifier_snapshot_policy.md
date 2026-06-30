# Expression Verified Identifier Snapshot Policy

Production precomputed expression import requires a configured
`expression.identifier_cache_dir` and `expression.identifier_snapshot_id`.

Synthetic and demonstration expression flows may create the bundled fixture
snapshot for local runs. Production import does not pick the first directory in a
cache implicitly; the configured snapshot id is the deterministic identifier
authority.
