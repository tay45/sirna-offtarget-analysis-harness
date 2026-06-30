from __future__ import annotations

from pathlib import Path
from typing import Any

from sirna_offtarget.contracts.base import StageContract
from sirna_offtarget.execution.hashing import sha256_file


def committed_artifact_catalog(run_dir: Path, contract: StageContract) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact in contract.artifacts:
        path = run_dir / artifact.relative_path
        rows.append(
            {
                "logical_name": artifact.logical_name,
                "relative_path": artifact.relative_path,
                "media_type": artifact.media_type,
                "sha256": sha256_file(path) if path.exists() else artifact.sha256,
                "size_bytes": path.stat().st_size if path.exists() else artifact.size_bytes,
                "required": artifact.required,
                "description": artifact.description,
            }
        )
    return rows
