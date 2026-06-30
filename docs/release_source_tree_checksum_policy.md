# Release Source Tree Checksum Policy

Policy version: `release-source-tree-checksum-v2`

The release source-tree checksum identifies the reproducible project source used for final tests, coverage, build, and packaging. It deliberately excludes release evidence files that are generated from the source tree so the checksum is not self-referential.

## Included Scope

The checksum includes project files under the release repository root unless they match an exclusion rule. This includes:

- `src/`
- `tests/`
- `docs/`
- `scripts/`
- `config/`
- `.github/`
- `resources/` and deterministic small fixtures
- `schemas/`
- `pyproject.toml`
- `README.md`
- `Dockerfile`
- other non-generated project source files needed to reproduce the release

## Excluded Scope

The checksum excludes:

- `LATEST.md`
- `release_manifest.json`
- `release_source_tree_inventory.json`
- `release_coverage_evidence.json`
- `post_package_verification.json`
- generated ZIP files
- `.coverage`
- `coverage.xml`
- `.git/`
- `.venv/`
- `work/`
- `build/`
- `dist/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `.import_linter_cache/`
- `examples/synthetic/output/`
- Python bytecode and local temporary files

## Algorithm

The shared implementation is `scripts.release_source_tree.compute_release_source_tree_checksum`.

It:

1. Resolves the repository root.
2. Requires root markers: `pyproject.toml`, `src`, and `tests`.
3. Walks files recursively.
4. Applies the same include and exclude rules everywhere.
5. Rejects symbolic links that leave the repository.
6. Normalizes paths to relative POSIX paths.
7. Sorts paths lexicographically.
8. Feeds each relative path, a NUL separator, the file bytes, and another NUL separator into SHA-256.
9. Returns the checksum, included-file count, and included path list.

Filesystem modification times and permissions are not part of the checksum.
