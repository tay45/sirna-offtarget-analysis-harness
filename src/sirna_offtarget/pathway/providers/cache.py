from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, cast

from sirna_offtarget.pathway.providers.exceptions import ProviderSnapshotError
from sirna_offtarget.pathway.providers.manifest import SCHEMA_VERSION, read_manifest, sha256_file


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(cast(Any, value)))
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def write_jsonl(path: Path, records: list[object]) -> None:
    path.write_text(
        "\n".join(json.dumps(to_jsonable(record), sort_keys=True) for record in records) + "\n"
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def latest_snapshot_dir(cache_dir: Path, provider: str) -> Path | None:
    provider_dir = cache_dir / provider
    if not provider_dir.exists():
        return None
    snapshots = sorted(path for path in provider_dir.iterdir() if path.is_dir())
    return snapshots[-1] if snapshots else None


def verify_cache(cache_dir: Path) -> list[str]:
    errors: list[str] = []
    snapshot_ids: set[str] = set()
    organisms: set[str] = set()
    for manifest_path in sorted(cache_dir.glob("*/*/provider_manifest.json")):
        try:
            manifest = read_manifest(manifest_path)
        except Exception as exc:  # pragma: no cover - defensive path
            errors.append(f"invalid manifest {manifest_path}: {exc}")
            continue
        if manifest.normalization_schema_version != SCHEMA_VERSION:
            errors.append(f"unsupported schema {manifest_path}")
        if manifest.snapshot_id in snapshot_ids:
            errors.append(f"duplicate snapshot id {manifest.snapshot_id}")
        snapshot_ids.add(manifest.snapshot_id)
        organisms.add(manifest.organism)
        root = manifest_path.parent
        for relative in (*manifest.raw_files, *manifest.normalized_files):
            path = root / ("raw" if relative in manifest.raw_files else "normalized") / relative
            if not path.exists():
                errors.append(f"missing cache file {path}")
                continue
            expected = manifest.file_checksums.get(relative)
            if expected and sha256_file(path) != expected:
                errors.append(f"checksum mismatch {path}")
        if manifest.completeness_status.startswith("incomplete"):
            errors.append(f"incomplete snapshot {manifest.snapshot_id}")
    if len(organisms) > 1:
        errors.append(f"inconsistent organisms: {sorted(organisms)}")
    for stale in cache_dir.glob("**/*.tmp"):
        errors.append(f"stale temporary file {stale}")
    return errors


def require_valid_cache(cache_dir: Path) -> None:
    errors = verify_cache(cache_dir)
    if errors:
        raise ProviderSnapshotError("; ".join(errors))


def assert_snapshot_immutable(snapshot_dir: Path) -> None:
    errors = verify_cache(snapshot_dir.parent.parent)
    if errors:
        raise ProviderSnapshotError("; ".join(errors))


def mark_verified(snapshot_dir: Path) -> None:
    marker = snapshot_dir / ".verified"
    marker.write_text("verified\n")


def is_verified(snapshot_dir: Path) -> bool:
    return (snapshot_dir / ".verified").exists() and not verify_cache(snapshot_dir.parent.parent)
