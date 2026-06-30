from __future__ import annotations

import hashlib
import json

import yaml

from sirna_offtarget.execution.api import run_staged_analysis
from sirna_offtarget.execution.hashing import load_json
from sirna_offtarget.transcript_targetability.artifacts import (
    verify_transcript_targetability_outputs,
)
from tests.integration.test_isoform_uncertainty_workflow_stage import (
    _write_annotation_cache,
    _write_targetability_config,
    _write_transcript_sequence_cache,
)


def _targetability_outputs(tmp_path, config_path):
    out = tmp_path / "run"
    run_staged_analysis(
        config_path=config_path,
        output_dir=out,
        until_stage="transcript_targetability",
    )
    return (
        out
        / "stages"
        / "07_transcript_targetability"
        / "attempts"
        / "attempt_001"
        / "committed"
        / "outputs"
    )


def test_original_transcript_independent_verification_pipeline(tmp_path) -> None:
    annotation_cache = _write_annotation_cache(tmp_path)
    config = _write_targetability_config(
        tmp_path,
        annotation_cache,
        _write_transcript_sequence_cache(tmp_path),
    )
    outputs = _targetability_outputs(tmp_path, config)

    verification = verify_transcript_targetability_outputs(outputs)

    assert verification["passed"]
    assert (outputs / "transcript_sequence_snapshot_records_v1.jsonl").exists()


def test_coordinated_fake_site_rejected_pipeline(tmp_path) -> None:
    annotation_cache = _write_annotation_cache(tmp_path)
    config = _write_targetability_config(
        tmp_path,
        annotation_cache,
        _write_transcript_sequence_cache(tmp_path),
    )
    outputs = _targetability_outputs(tmp_path, config)
    sites_path = outputs / "transcript_targetability_sites_v1.jsonl"
    rows = [json.loads(line) for line in sites_path.read_text().splitlines() if line.strip()]
    rows[0]["transcript_site_sequence"] = "A" * rows[0]["alignment_length"]
    sites_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))

    verification = verify_transcript_targetability_outputs(outputs)

    assert not verification["passed"]
    assert any(error.startswith("site_sequence_mismatch:") for error in verification["errors"])


def test_fail_gene_pipeline(tmp_path) -> None:
    annotation_cache = _write_annotation_cache(tmp_path)
    sequence_cache = _write_transcript_sequence_cache(tmp_path)
    records = sequence_cache / "synthetic-v1" / "transcript_sequences.jsonl"
    rows = [
        json.loads(line)
        for line in records.read_text().splitlines()
        if line.strip() and "target1_tx2" not in line
    ]
    records.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    manifest_path = sequence_cache / "synthetic-v1" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["transcript_count"] = len(rows)
    manifest["sequence_file_checksum"] = hashlib.sha256(records.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    config = _write_targetability_config(tmp_path, annotation_cache, sequence_cache)
    payload = yaml.safe_load(config.read_text())
    payload["transcript_targetability"]["missing_transcript_sequence_mode"] = "fail_gene"
    payload["transcript_targetability"]["intended_target_failure_behavior"] = "warning"
    config.write_text(yaml.safe_dump(payload, sort_keys=False))

    outputs = _targetability_outputs(tmp_path, config)
    result = load_json(outputs / "transcript_targetability_result_v1.json")
    failures = [
        json.loads(line)
        for line in (outputs / "transcript_targetability_gene_failures_v1.jsonl")
        .read_text()
        .splitlines()
        if line.strip()
    ]

    assert failures
    assert result["counts"]["genes_failed_under_fail_gene"] == 1
    assert result["counts"]["transcripts_not_evaluated_due_to_gene_failure"] >= 1
    assert verify_transcript_targetability_outputs(outputs)["passed"]


def test_gene_only_behavior_pipeline(tmp_path) -> None:
    annotation_cache = _write_annotation_cache(tmp_path)
    config = _write_targetability_config(
        tmp_path,
        annotation_cache,
        _write_transcript_sequence_cache(tmp_path),
    )
    payload = yaml.safe_load(config.read_text())
    payload["transcript_targetability"]["intended_target_gene_only_behavior"] = (
        "preserve_uncertainty"
    )
    config.write_text(yaml.safe_dump(payload, sort_keys=False))
    outputs = _targetability_outputs(tmp_path, config)
    validation = load_json(outputs / "intended_target_validation_v1.json")

    assert validation["validation_status"] == "uncertain"
