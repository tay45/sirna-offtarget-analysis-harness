from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ArtifactReference(BaseModel):
    logical_name: str
    relative_path: str
    media_type: str
    schema_name: str | None = None
    schema_version: str | None = None
    sha256: str
    size_bytes: int
    row_count: int | None = None
    created_by_stage: str
    created_by_attempt: int
    required: bool = True
    description: str = ""


class ContractProvenance(BaseModel):
    dependency_contract_hashes: dict[str, str] = Field(default_factory=dict)
    fingerprint_hash: str | None = None
    config_revision: int = 1
    extra: dict[str, Any] = Field(default_factory=dict)


def build_artifact_reference(
    *,
    run_dir: Path,
    path: Path,
    logical_name: str,
    media_type: str,
    created_by_stage: str,
    created_by_attempt: int,
    schema_name: str | None = None,
    schema_version: str | None = None,
    required: bool = True,
    description: str = "",
) -> ArtifactReference:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return ArtifactReference(
        logical_name=logical_name,
        relative_path=str(path.relative_to(run_dir)),
        media_type=media_type,
        schema_name=schema_name,
        schema_version=schema_version,
        sha256=digest.hexdigest(),
        size_bytes=path.stat().st_size,
        created_by_stage=created_by_stage,
        created_by_attempt=created_by_attempt,
        required=required,
        description=description,
    )
