from __future__ import annotations

import json
from pathlib import Path

from sirna_offtarget.isoform_uncertainty.artifacts import (
    artifact_paths,
    sha256_file,
    verify_committed_isoform_uncertainty_result,
    verify_isoform_uncertainty_final_outputs,
)
from tests.unit.isoform_uncertainty.finalization.test_artifact_finalization_policy import (
    _finalize,
)


def _write_manifest(attempt_dir: Path) -> None:
    output_dir = attempt_dir / "committed" / "outputs"
    checksums = {
        str(path.relative_to(attempt_dir)): sha256_file(path)
        for path in artifact_paths(output_dir).values()
    }
    checksums["committed/outputs/stage_result.json"] = "stage-result-checksum"
    (attempt_dir / "stage_manifest.json").write_text(
        json.dumps(
            {
                "stage_name": "isoform_uncertainty",
                "status": "completed",
                "output_sha256_checksums": checksums,
            },
            sort_keys=True,
        )
        + "\n"
    )


def _committed_attempt(tmp_path: Path, snapshot, policy) -> Path:
    attempt_dir = tmp_path / "attempt_001"
    output_dir = attempt_dir / "committed" / "outputs"
    output_dir.mkdir(parents=True)
    _finalize(output_dir, snapshot, policy)
    (output_dir / "stage_result.json").write_text("{}\n")
    _write_manifest(attempt_dir)
    return attempt_dir


def test_precommit_verifies_final_file_checksums(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    verification = verify_isoform_uncertainty_final_outputs(tmp_path)
    assert verification.passed
    assert verification.final_checksums["run"] == sha256_file(
        tmp_path / "isoform_uncertainty_run_v1.json"
    )


def test_precommit_detects_stale_referenced_checksum(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    run_path = tmp_path / "isoform_uncertainty_run_v1.json"
    run = json.loads(run_path.read_text())
    run["referenced_artifact_checksums"]["genes"] = "stale"
    run_path.write_text(json.dumps(run, sort_keys=True) + "\n")
    verification = verify_isoform_uncertainty_final_outputs(tmp_path)
    assert "stale_referenced_checksum:genes" in verification.errors


def test_precommit_detects_missing_artifact(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    (tmp_path / "gene_isoform_uncertainty_v1.jsonl").unlink()
    verification = verify_isoform_uncertainty_final_outputs(tmp_path)
    assert "missing_artifact:gene_isoform_uncertainty_v1.jsonl" in verification.errors


def test_precommit_detects_empty_required_artifact(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    (tmp_path / "transcript_annotation_validation_v1.json").write_text("")
    verification = verify_isoform_uncertainty_final_outputs(tmp_path)
    assert "empty_artifact:transcript_annotation_validation_v1.json" in verification.errors


def test_precommit_detects_count_mismatch(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    run_path = tmp_path / "isoform_uncertainty_run_v1.json"
    run = json.loads(run_path.read_text())
    run["record_counts"]["gene_isoform_uncertainty_records"] = 99
    run_path.write_text(json.dumps(run, sort_keys=True) + "\n")
    verification = verify_isoform_uncertainty_final_outputs(tmp_path)
    assert "count_mismatch:gene_isoform_uncertainty_records" in verification.errors


def test_precommit_detects_schema_mismatch(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    (tmp_path / "isoform_input_validation_v1.json").write_text("{")
    verification = verify_isoform_uncertainty_final_outputs(tmp_path)
    assert "schema_mismatch:input_validation" in verification.errors


def test_precommit_detects_incomplete_run(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    run_path = tmp_path / "isoform_uncertainty_run_v1.json"
    run = json.loads(run_path.read_text())
    run["status"] = "failed"
    run_path.write_text(json.dumps(run, sort_keys=True) + "\n")
    assert "run_record_not_completed" in verify_isoform_uncertainty_final_outputs(tmp_path).errors


def test_precommit_detects_deprecated_output_checksums(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    run_path = tmp_path / "isoform_uncertainty_run_v1.json"
    run = json.loads(run_path.read_text())
    run["output_checksums"] = {"run": "self"}
    run_path.write_text(json.dumps(run, sort_keys=True) + "\n")
    verification = verify_isoform_uncertainty_final_outputs(tmp_path)
    assert "run_record_contains_deprecated_output_checksums" in verification.errors


def test_precommit_detects_result_run_reference_mismatch(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    result_path = tmp_path / "isoform_uncertainty_result_v1.json"
    result = json.loads(result_path.read_text())
    result["run_record"]["run_id"] = "other"
    result_path.write_text(json.dumps(result, sort_keys=True) + "\n")
    verification = verify_isoform_uncertainty_final_outputs(tmp_path)
    assert "result_run_reference_mismatch" in verification.errors


def test_precommit_detects_unreadable_result_record(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    (tmp_path / "isoform_uncertainty_result_v1.json").write_text("{")
    verification = verify_isoform_uncertainty_final_outputs(tmp_path)
    assert any(error.startswith("result_record_unreadable") for error in verification.errors)


def test_precommit_passes_valid_final_output(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    assert verify_isoform_uncertainty_final_outputs(tmp_path).passed


def test_failed_precommit_does_not_commit(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    (tmp_path / "isoform_uncertainty_run_v1.json").write_text("{}\n")
    assert not verify_isoform_uncertainty_final_outputs(tmp_path).passed


def test_postcommit_recomputes_all_checksums(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    assert verify_committed_isoform_uncertainty_result(attempt).passed


def test_postcommit_detects_modified_scientific_artifact(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    (attempt / "committed/outputs/gene_isoform_uncertainty_v1.jsonl").write_text("{}\n")
    assert not verify_committed_isoform_uncertainty_result(attempt).passed


def test_postcommit_detects_modified_run_record(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    (attempt / "committed/outputs/isoform_uncertainty_run_v1.json").write_text("{}\n")
    assert not verify_committed_isoform_uncertainty_result(attempt).passed


def test_postcommit_detects_modified_result_record(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    (attempt / "committed/outputs/isoform_uncertainty_result_v1.json").write_text("{}\n")
    assert not verify_committed_isoform_uncertainty_result(attempt).passed


def test_postcommit_detects_modified_report_view(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    (attempt / "committed/outputs/isoform_uncertainty_summary_v1.json").write_text("{}\n")
    assert not verify_committed_isoform_uncertainty_result(attempt).passed


def test_postcommit_detects_missing_manifest_entry(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    manifest_path = attempt / "stage_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["output_sha256_checksums"].pop("committed/outputs/isoform_uncertainty_run_v1.json")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
    verification = verify_committed_isoform_uncertainty_result(attempt)
    assert "missing_manifest_entry:isoform_uncertainty_run_v1.json" in verification.errors


def test_postcommit_detects_missing_stage_manifest(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    (attempt / "stage_manifest.json").unlink()
    verification = verify_committed_isoform_uncertainty_result(attempt)
    assert "missing_stage_manifest" in verification.errors


def test_postcommit_detects_unexpected_artifact(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    (attempt / "committed/outputs/unexpected.txt").write_text("x")
    verification = verify_committed_isoform_uncertainty_result(attempt)
    assert any(error.startswith("unexpected_artifact") for error in verification.errors)


def test_postcommit_detects_record_count_change(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    (attempt / "committed/outputs/gene_isoform_uncertainty_v1.jsonl").write_text("{}\n{}\n")
    verification = verify_committed_isoform_uncertainty_result(attempt)
    assert any(error.startswith("count_mismatch") for error in verification.errors)


def test_postcommit_accepts_valid_committed_result(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    assert verify_committed_isoform_uncertainty_result(attempt).passed


def test_corrupt_committed_result_not_resumed(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    (attempt / "committed/outputs/isoform_uncertainty_run_v1.json").write_text("{}\n")
    assert not verify_committed_isoform_uncertainty_result(attempt).passed


def test_outer_manifest_records_run_file_checksum(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    manifest = json.loads((attempt / "stage_manifest.json").read_text())
    key = "committed/outputs/isoform_uncertainty_run_v1.json"
    assert manifest["output_sha256_checksums"][key] == sha256_file(attempt / key)


def test_outer_manifest_records_result_file_checksum(tmp_path, snapshot, policy) -> None:
    attempt = _committed_attempt(tmp_path, snapshot, policy)
    manifest = json.loads((attempt / "stage_manifest.json").read_text())
    key = "committed/outputs/isoform_uncertainty_result_v1.json"
    assert manifest["output_sha256_checksums"][key] == sha256_file(attempt / key)
