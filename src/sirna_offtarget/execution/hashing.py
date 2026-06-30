from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def hash_data(data: Any) -> str:
    return sha256_bytes(canonical_json(data).encode())


def read_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError("configuration YAML must be a mapping")
    return raw


def write_yaml(path: Path, data: Any) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def dump_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def artifact_record(path: Path, base: Path | None = None) -> dict[str, Any]:
    rel = path.relative_to(base) if base and path.is_relative_to(base) else path
    record: dict[str, Any] = {"path": str(rel), "exists": path.exists()}
    if path.exists() and path.is_file():
        record["sha256"] = sha256_file(path)
        record["size_bytes"] = path.stat().st_size
    return record
