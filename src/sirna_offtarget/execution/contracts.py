from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from sirna_offtarget.contracts.base import StageContract
from sirna_offtarget.contracts.exceptions import (
    ArtifactIntegrityError,
    ContractCompatibilityError,
)
from sirna_offtarget.contracts.validation import (
    validate_contract_artifacts,
    validate_contract_file,
)
from sirna_offtarget.execution.checkpoints import current_manifest_path
from sirna_offtarget.execution.dag import stage_index
from sirna_offtarget.execution.hashing import load_json, sha256_file
from sirna_offtarget.execution.state import RunContext

T = TypeVar("T", bound=StageContract)


def stage_directory(run_dir: Path, stage_name: str) -> Path:
    return run_dir / "stages" / f"{stage_index(stage_name):02d}_{stage_name}"


def committed_contract_path(run_dir: Path, dependency_stage: str) -> Path:
    manifest_path = current_manifest_path(stage_directory(run_dir, dependency_stage))
    if manifest_path is None:
        raise ContractCompatibilityError(f"{dependency_stage} has no current successful attempt")
    manifest = load_json(manifest_path)
    if manifest.get("status") not in {"completed", "completed_with_warnings"}:
        raise ContractCompatibilityError(
            f"{dependency_stage} current attempt status is {manifest.get('status')}"
        )
    contract_path = manifest_path.parent / "committed" / "outputs" / "stage_result.json"
    if not contract_path.exists():
        raise ContractCompatibilityError(f"{dependency_stage} missing committed stage_result.json")
    expected_hash = manifest.get("contract_sha256")
    if expected_hash and sha256_file(contract_path) != expected_hash:
        raise ArtifactIntegrityError(f"{dependency_stage} contract checksum mismatch")
    return contract_path


def load_dependency_contract(
    context: RunContext,
    *,
    dependency_stage: str,
    expected_contract: type[T],
) -> T:
    path = committed_contract_path(context.run_dir, dependency_stage)
    contract = validate_contract_file(path, expected_contract)
    validate_contract_artifacts(context.run_dir, contract)
    return contract
