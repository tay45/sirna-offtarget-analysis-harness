from __future__ import annotations

import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sirna_offtarget import __version__
from sirna_offtarget.execution.hashing import artifact_record, dump_json, hash_data, load_json

MANIFEST_SCHEMA_VERSION = "1"
STATUS_VALUES = {
    "pending",
    "running",
    "completed",
    "completed_with_warnings",
    "failed",
    "interrupted",
    "blocked",
    "invalidated",
    "skipped_reused",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def manifest_hash(path: Path) -> str:
    data = load_json(path)
    return hash_data(data)


def write_stage_manifest(attempt_dir: Path, manifest: dict[str, Any]) -> Path:
    status = str(manifest.get("status", "pending"))
    if status not in STATUS_VALUES:
        raise ValueError(f"unsupported stage status {status}")
    path = attempt_dir / "stage_manifest.json"
    dump_json(path, manifest)
    return path


def build_base_manifest(
    *,
    run_id: str,
    stage_name: str,
    stage_version: str,
    attempt_number: int,
    status: str,
    started_at: str,
    original_config_hash: str,
    resolved_config_hash: str,
    relevant_config_hash: str,
    stage_fingerprint: str,
    dependencies: list[str],
    command_invocation: tuple[str, ...],
    offline: bool,
) -> dict[str, Any]:
    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "stage_name": stage_name,
        "stage_version": stage_version,
        "attempt_number": attempt_number,
        "status": status,
        "started_at": started_at,
        "completed_at": None,
        "elapsed_seconds": None,
        "software_version": __version__,
        "code_commit": None,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "original_config_hash": original_config_hash,
        "resolved_config_hash": resolved_config_hash,
        "relevant_config_hash": relevant_config_hash,
        "stage_fingerprint": stage_fingerprint,
        "input_artifacts": [],
        "input_sha256_checksums": {},
        "dependency_stage_names": dependencies,
        "dependency_manifest_hashes": {},
        "dependency_output_hashes": {},
        "output_artifacts": [],
        "output_sha256_checksums": {},
        "output_schema_versions": {},
        "warning_count": 0,
        "error_count": 0,
        "report_paths": {},
        "command_invocation": list(command_invocation),
        "offline": offline,
        "provider_cache_snapshot_identifiers": [],
        "reproducibility_metadata": {},
    }


def attach_artifacts(
    manifest: dict[str, Any],
    *,
    inputs: list[Path],
    outputs: list[Path],
    base: Path,
) -> None:
    manifest["input_artifacts"] = [artifact_record(path, base) for path in inputs]
    manifest["input_sha256_checksums"] = {
        record["path"]: record["sha256"]
        for record in manifest["input_artifacts"]
        if record.get("sha256")
    }
    manifest["output_artifacts"] = [artifact_record(path, base) for path in outputs]
    manifest["output_sha256_checksums"] = {
        record["path"]: record["sha256"]
        for record in manifest["output_artifacts"]
        if record.get("sha256")
    }
