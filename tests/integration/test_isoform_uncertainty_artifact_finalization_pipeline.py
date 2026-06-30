from __future__ import annotations

import json
from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis
from sirna_offtarget.execution.hashing import load_json, sha256_file
from sirna_offtarget.isoform_uncertainty.artifacts import (
    verify_committed_isoform_uncertainty_result,
)
from tests.integration.test_isoform_uncertainty_workflow_stage import (
    _write_annotation_cache,
    _write_config,
)


def _run(tmp_path: Path) -> Path:
    config_path = _write_config(tmp_path, _write_annotation_cache(tmp_path))
    out = tmp_path / "run"
    run_staged_analysis(
        config_path=config_path,
        output_dir=out,
        until_stage="isoform_uncertainty",
    )
    return out


def _attempt(out: Path, attempt: str = "attempt_001") -> Path:
    return out / "stages" / "06_isoform_uncertainty" / "attempts" / attempt


def test_isoform_uncertainty_final_artifact_checksum_pipeline(tmp_path: Path) -> None:
    attempt = _attempt(_run(tmp_path))
    manifest = load_json(attempt / "stage_manifest.json")
    for record in manifest["output_artifacts"]:
        path = attempt / record["path"]
        assert record["sha256"] == sha256_file(path)


def test_isoform_uncertainty_precommit_verification_pipeline(tmp_path: Path) -> None:
    attempt = _attempt(_run(tmp_path))
    assert verify_committed_isoform_uncertainty_result(attempt).passed


def test_isoform_uncertainty_stale_checksum_rejected_pipeline(tmp_path: Path) -> None:
    attempt = _attempt(_run(tmp_path))
    run_path = attempt / "committed" / "outputs" / "isoform_uncertainty_run_v1.json"
    payload = json.loads(run_path.read_text())
    payload["referenced_artifact_checksums"]["genes"] = "stale"
    run_path.write_text(json.dumps(payload, sort_keys=True) + "\n")
    assert not verify_committed_isoform_uncertainty_result(attempt).passed


def test_isoform_uncertainty_modified_artifact_rejected_pipeline(tmp_path: Path) -> None:
    attempt = _attempt(_run(tmp_path))
    (attempt / "committed" / "outputs" / "gene_isoform_uncertainty_v1.jsonl").write_text("{}\n")
    assert not verify_committed_isoform_uncertainty_result(attempt).passed


def test_isoform_uncertainty_atomic_commit_pipeline(tmp_path: Path) -> None:
    attempt = _attempt(_run(tmp_path))
    assert (attempt / "committed" / "outputs" / "stage_result.json").exists()
    assert load_json(attempt / "stage_manifest.json")["status"] == "completed_with_warnings"


def test_isoform_uncertainty_resume_verifies_checksums_pipeline(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, _write_annotation_cache(tmp_path))
    out = tmp_path / "run"
    run_staged_analysis(config_path=config_path, output_dir=out, until_stage="isoform_uncertainty")
    rows = run_staged_analysis(
        config_path=config_path,
        output_dir=out,
        until_stage="isoform_uncertainty",
    )
    assert rows[-1]["action"] == "reuse"


def test_isoform_uncertainty_corrupt_commit_reruns_pipeline(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, _write_annotation_cache(tmp_path))
    out = tmp_path / "run"
    run_staged_analysis(config_path=config_path, output_dir=out, until_stage="isoform_uncertainty")
    (
        out
        / "stages/06_isoform_uncertainty/attempts/attempt_001/committed/outputs"
        / "gene_isoform_uncertainty_v1.jsonl"
    ).write_text("{}\n")
    rows = run_staged_analysis(
        config_path=config_path,
        output_dir=out,
        until_stage="isoform_uncertainty",
    )
    assert rows[-1]["action"] == "run"
    assert _attempt(out, "attempt_002").exists()


def test_isoform_uncertainty_run_result_reference_pipeline(tmp_path: Path) -> None:
    result = load_json(
        _attempt(_run(tmp_path)) / "committed" / "outputs" / "isoform_uncertainty_result_v1.json"
    )
    assert result["run_record"]["run_id"] == "latest"
    assert result["run_record_file_sha256"]
