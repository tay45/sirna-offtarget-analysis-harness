# Pathway Cache

Normal analysis is offline. `sirna-offtarget pathway-db fetch` writes provider
snapshots under `provider/snapshot_id/{raw,normalized}` with
`provider_manifest.json`, checksums, record counts, schema version, organism,
retrieval timestamp, database version, and license notes.

`pathway-db inspect` lists snapshots. `pathway-db verify` validates manifests,
checksums, schema versions, organisms, incomplete snapshots, and stale temporary
files, then writes `pathway_cache_verification.json` and `.html`.

