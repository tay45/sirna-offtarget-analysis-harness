from __future__ import annotations

import json
from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis
from sirna_offtarget.execution.dag import stage_index
from sirna_offtarget.transcript_targetability_ratio.artifacts import (
    verify_transcript_targetability_ratio_outputs,
)
from tests.integration.test_isoform_uncertainty_workflow_stage import (
    _write_annotation_cache,
    _write_targetability_config,
    _write_transcript_sequence_cache,
)


def _ratio_outputs(out: Path) -> Path:
    return (
        out
        / "stages"
        / f"{stage_index('transcript_targetability_ratio'):02d}_transcript_targetability_ratio"
        / "attempts"
        / "attempt_001"
        / "committed"
        / "outputs"
    )


def test_isoform_and_targetability_to_ratio_pipeline(tmp_path: Path) -> None:
    annotation_cache = _write_annotation_cache(tmp_path)
    sequence_cache = _write_transcript_sequence_cache(tmp_path)
    config_path = _write_targetability_config(tmp_path, annotation_cache, sequence_cache)
    out = tmp_path / "run"

    rows = run_staged_analysis(
        config_path=config_path, output_dir=out, until_stage="transcript_targetability_ratio"
    )

    assert rows[-1]["stage"] == "transcript_targetability_ratio"
    outputs = _ratio_outputs(out)
    assert verify_transcript_targetability_ratio_outputs(outputs)["passed"]
    summary = json.loads((outputs / "transcript_targetability_ratio_summary_v1.json").read_text())
    assert summary["genes_examined"] > 0
    assert summary["total_eligible_transcripts"] > 0


def test_ratio_commit_and_resume_pipeline(tmp_path: Path) -> None:
    annotation_cache = _write_annotation_cache(tmp_path)
    sequence_cache = _write_transcript_sequence_cache(tmp_path)
    config_path = _write_targetability_config(tmp_path, annotation_cache, sequence_cache)
    out = tmp_path / "run"

    first = run_staged_analysis(
        config_path=config_path, output_dir=out, until_stage="transcript_targetability_ratio"
    )
    second = run_staged_analysis(
        config_path=config_path, output_dir=out, until_stage="transcript_targetability_ratio"
    )

    assert first[-1]["action"] == "run"
    assert second[-1]["stage"] == "transcript_targetability_ratio"
    assert second[-1]["action"] == "reuse"
