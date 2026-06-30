from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypeVar

from sirna_offtarget.contracts.base import StageContract
from sirna_offtarget.contracts.exceptions import (
    ArtifactIntegrityError,
    ContractCompatibilityError,
)

T = TypeVar("T", bound=StageContract)


def validate_contract_file(path: Path, expected_contract: type[T]) -> T:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ContractCompatibilityError(f"{path} must contain a JSON object")
    try:
        return expected_contract.model_validate(data)
    except ValueError as exc:
        raise ContractCompatibilityError(str(exc)) from exc


def validate_contract_artifacts(run_dir: Path, contract: StageContract) -> None:
    for artifact in contract.artifacts:
        path = run_dir / artifact.relative_path
        if artifact.required and not path.exists():
            raise ArtifactIntegrityError(f"missing artifact {artifact.relative_path}")
        if path.exists() and _sha256_file(path) != artifact.sha256:
            raise ArtifactIntegrityError(f"checksum mismatch for {artifact.relative_path}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
