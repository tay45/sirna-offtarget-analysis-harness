from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sirna_offtarget.pathway.providers.models import ProviderManifest

SCHEMA_VERSION = "provider-cache-v2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_id(provider: str, organism: str, payload: object) -> str:
    seed = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(seed.encode()).hexdigest()[:12]
    return f"{provider}_{organism}_{digest}_{SCHEMA_VERSION}"


def build_provider_manifest(
    *,
    provider: str,
    snapshot: str,
    organism: str,
    endpoint: str,
    request_parameters: dict[str, str],
    database_version: str,
    raw_files: list[Path],
    normalized_files: list[Path],
    record_counts: dict[str, int],
    warnings: list[str],
    license_notes: str,
) -> ProviderManifest:
    files = raw_files + normalized_files
    return ProviderManifest(
        provider=provider,
        snapshot_id=snapshot,
        organism=organism,
        endpoint=endpoint,
        request_parameters=request_parameters,
        retrieval_timestamp=datetime.now(UTC).isoformat(),
        database_version=database_version,
        api_version=None,
        normalization_schema_version=SCHEMA_VERSION,
        raw_files=tuple(str(path.name) for path in raw_files),
        normalized_files=tuple(str(path.name) for path in normalized_files),
        file_checksums={path.name: sha256_file(path) for path in files},
        record_counts=record_counts,
        warning_count=len(warnings),
        license_notes=license_notes,
        completeness_status="complete" if not warnings else "complete_with_warnings",
    )


def write_manifest(path: Path, manifest: ProviderManifest) -> None:
    path.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n")


def read_manifest(path: Path) -> ProviderManifest:
    data: dict[str, Any] = json.loads(path.read_text())
    return ProviderManifest(
        provider=str(data["provider"]),
        snapshot_id=str(data["snapshot_id"]),
        organism=str(data["organism"]),
        endpoint=str(data["endpoint"]),
        request_parameters={str(k): str(v) for k, v in data.get("request_parameters", {}).items()},
        retrieval_timestamp=str(data["retrieval_timestamp"]),
        database_version=str(data["database_version"]),
        api_version=data.get("api_version"),
        normalization_schema_version=str(data["normalization_schema_version"]),
        raw_files=tuple(data.get("raw_files", ())),
        normalized_files=tuple(data.get("normalized_files", ())),
        file_checksums={str(k): str(v) for k, v in data.get("file_checksums", {}).items()},
        record_counts={str(k): int(v) for k, v in data.get("record_counts", {}).items()},
        warning_count=int(data.get("warning_count", 0)),
        license_notes=str(data.get("license_notes", "")),
        completeness_status=str(data.get("completeness_status", "unknown")),
    )
