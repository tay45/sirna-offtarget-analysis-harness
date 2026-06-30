from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sirna_offtarget.contracts.artifacts import ArtifactReference
from sirna_offtarget.contracts.base import StageContract, make_contract
from sirna_offtarget.contracts.exceptions import (
    ArtifactIntegrityError,
    ContractCompatibilityError,
)
from sirna_offtarget.contracts.validation import (
    validate_contract_artifacts,
    validate_contract_file,
)
from sirna_offtarget.execution.atomic import read_current_pointer, write_current_pointer
from sirna_offtarget.execution.attempts import list_attempts
from sirna_offtarget.execution.checkpoints import (
    current_attempt_dir,
    current_manifest_path,
    next_attempt_number,
)
from sirna_offtarget.execution.contracts import committed_contract_path
from sirna_offtarget.execution.hashing import artifact_record, load_json, read_yaml
from sirna_offtarget.validation.result_validation import validate_output_directory
from sirna_offtarget.validation.schema import required_output_files


def _artifact(path: str, sha256: str, *, required: bool = True) -> ArtifactReference:
    return ArtifactReference(
        logical_name=path,
        relative_path=path,
        media_type="text/plain",
        sha256=sha256,
        size_bytes=1,
        created_by_stage="expression_analysis",
        created_by_attempt=1,
        required=required,
    )


def test_contract_file_rejects_non_object_and_invalid_identity(tmp_path: Path) -> None:
    non_object = tmp_path / "list.json"
    non_object.write_text("[]")
    with pytest.raises(ContractCompatibilityError, match="JSON object"):
        validate_contract_file(non_object, StageContract)

    wrong_identity = tmp_path / "wrong.json"
    wrong_identity.write_text(
        json.dumps(
            {
                "contract_name": "WrongContract",
                "schema_version": "1",
                "stage_name": "expression_analysis",
                "stage_version": "1.0",
                "run_id": "run",
                "attempt_number": 1,
                "payload": {"ok": True},
            }
        )
    )
    with pytest.raises(ContractCompatibilityError, match="expected StageContract"):
        validate_contract_file(wrong_identity, StageContract)


def test_contract_artifact_validation_distinguishes_missing_optional_and_bad_hash(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "payload.txt"
    payload.write_text("ok")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    contract = make_contract(
        StageContract,
        stage_name="expression_analysis",
        stage_version="1.0",
        run_id="run",
        attempt_number=1,
        payload={"ok": True},
        artifacts=[
            _artifact("payload.txt", digest),
            _artifact("optional.txt", "unused", required=False),
        ],
        warnings=[],
    )
    validate_contract_artifacts(tmp_path, contract)

    missing_required = contract.model_copy(update={"artifacts": [_artifact("missing.txt", digest)]})
    with pytest.raises(ArtifactIntegrityError, match="missing artifact"):
        validate_contract_artifacts(tmp_path, missing_required)

    bad_hash = contract.model_copy(update={"artifacts": [_artifact("payload.txt", "bad")]})
    with pytest.raises(ArtifactIntegrityError, match="checksum mismatch"):
        validate_contract_artifacts(tmp_path, bad_hash)


def test_checkpoint_helpers_resolve_current_attempts_and_ignore_bad_names(tmp_path: Path) -> None:
    stage_dir = tmp_path / "stages" / "05_expression_analysis"
    assert current_manifest_path(stage_dir) is None
    assert current_attempt_dir(stage_dir) is None

    attempts = stage_dir / "attempts"
    (attempts / "attempt_002").mkdir(parents=True)
    (attempts / "attempt_bad").mkdir()
    assert next_attempt_number(stage_dir) == 3

    (stage_dir / "current.json").write_text(json.dumps({"attempt_directory": "attempt_001"}))
    assert current_manifest_path(stage_dir) is None
    assert current_attempt_dir(stage_dir) is None

    attempt = attempts / "attempt_001"
    attempt.mkdir()
    manifest = attempt / "stage_manifest.json"
    manifest.write_text(json.dumps({"status": "completed"}))
    assert current_manifest_path(stage_dir) == manifest
    assert current_attempt_dir(stage_dir) == attempt


def test_committed_contract_path_reports_manifest_failures(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    with pytest.raises(ContractCompatibilityError, match="no current successful attempt"):
        committed_contract_path(run_dir, "expression_analysis")

    attempt = run_dir / "stages" / "05_expression_analysis" / "attempts" / "attempt_001"
    attempt.mkdir(parents=True)
    current = run_dir / "stages" / "05_expression_analysis" / "current.json"
    current.write_text(json.dumps({"attempt_directory": "attempt_001"}))
    manifest = attempt / "stage_manifest.json"
    manifest.write_text(json.dumps({"status": "failed"}))
    with pytest.raises(ContractCompatibilityError, match="status is failed"):
        committed_contract_path(run_dir, "expression_analysis")

    manifest.write_text(json.dumps({"status": "completed_with_warnings"}))
    with pytest.raises(ContractCompatibilityError, match="missing committed"):
        committed_contract_path(run_dir, "expression_analysis")

    contract = attempt / "committed" / "outputs" / "stage_result.json"
    contract.parent.mkdir(parents=True)
    contract.write_text("{}")
    manifest.write_text(json.dumps({"status": "completed", "contract_sha256": "bad"}))
    with pytest.raises(ArtifactIntegrityError, match="checksum mismatch"):
        committed_contract_path(run_dir, "expression_analysis")

    digest = hashlib.sha256(contract.read_bytes()).hexdigest()
    manifest.write_text(json.dumps({"status": "completed", "contract_sha256": digest}))
    assert committed_contract_path(run_dir, "expression_analysis") == contract


def test_atomic_pointer_and_attempt_listing_helpers_validate_json_shape(tmp_path: Path) -> None:
    stage_dir = tmp_path / "stages" / "05_expression_analysis"
    attempt_dir = stage_dir / "attempts" / "attempt_001"
    attempt_dir.mkdir(parents=True)
    assert read_current_pointer(stage_dir) is None

    write_current_pointer(stage_dir, 1, attempt_dir)
    assert read_current_pointer(stage_dir) == {
        "attempt_number": 1,
        "attempt_directory": "attempt_001",
    }

    run_dir = tmp_path / "run"
    assert list_attempts(run_dir, "expression_analysis") == []
    manifest = run_dir / "stages" / "05_expression_analysis" / "attempts" / "attempt_001"
    manifest.mkdir(parents=True)
    (manifest / "stage_manifest.json").write_text(json.dumps({"status": "completed"}))
    assert list_attempts(run_dir, "expression_analysis") == [{"status": "completed"}]

    (stage_dir / "current.json").write_text("[]")
    with pytest.raises(ValueError, match="JSON object"):
        read_current_pointer(stage_dir)


def test_hashing_loaders_and_artifact_records_cover_absent_and_present_files(
    tmp_path: Path,
) -> None:
    empty_yaml = tmp_path / "empty.yaml"
    empty_yaml.write_text("")
    assert read_yaml(empty_yaml) == {}
    list_yaml = tmp_path / "list.yaml"
    list_yaml.write_text("- a\n")
    with pytest.raises(ValueError, match="mapping"):
        read_yaml(list_yaml)

    list_json = tmp_path / "list.json"
    list_json.write_text("[]")
    with pytest.raises(ValueError, match="JSON object"):
        load_json(list_json)

    missing = tmp_path / "missing.txt"
    assert artifact_record(missing, tmp_path) == {"path": "missing.txt", "exists": False}
    outside = tmp_path.parent / "outside-artifact.txt"
    outside.write_text("outside")
    record = artifact_record(outside, tmp_path)
    assert record["path"] == str(outside)
    assert record["exists"] is True
    assert record["size_bytes"] == len("outside")


def test_output_directory_validation_reports_missing_current_ratio_files(tmp_path: Path) -> None:
    for name in required_output_files():
        (tmp_path / name).write_text("")
    (tmp_path / "transcript_targetability_ratio_summary_v1.json").unlink()

    errors = validate_output_directory(tmp_path)

    assert "missing output file: transcript_targetability_ratio_summary_v1.json" in errors
