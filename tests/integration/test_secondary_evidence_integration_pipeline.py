from __future__ import annotations

import json
from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis, verify_run
from sirna_offtarget.execution.dag import stage_index
from sirna_offtarget.secondary_evidence_integration.artifacts import (
    verify_secondary_evidence_integration_outputs,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "examples/portfolio/config.yaml"


def _outputs(out: Path, stage: str) -> Path:
    return (
        out
        / "stages"
        / f"{stage_index(stage):02d}_{stage}"
        / "attempts"
        / "attempt_001"
        / "committed"
        / "outputs"
    )


def test_secondary_evidence_integration_default_pipeline_outputs_verify(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(config_path=CONFIG, output_dir=out)
    assert rows[-1]["stage"] == "secondary_evidence_integration"
    outputs = _outputs(out, "secondary_evidence_integration")
    assert verify_secondary_evidence_integration_outputs(outputs)["passed"]
    assert verify_run(out) == []
    summary = json.loads((outputs / "secondary_evidence_integration_summary_v1.json").read_text())
    assert summary["classification_performed"] is False
    assert summary["classification_ready_evidence_only"] is True
    records = [
        json.loads(line)
        for line in (outputs / "gene_secondary_evidence_integration_v1.jsonl")
        .read_text()
        .splitlines()
        if line.strip()
    ]
    assert records
    assert all(record["evidence_readiness_status"] for record in records)
    assert all("final_classification" not in record for record in records)


def test_until_residual_attribution_still_stops_there(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG, output_dir=out, until_stage="residual_attribution"
    )
    assert rows[-1]["stage"] == "residual_attribution"
    assert not _outputs(out, "secondary_evidence_integration").exists()


def test_until_expected_direct_effect_still_stops_before_integration(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG, output_dir=out, until_stage="expected_direct_effect"
    )
    assert rows[-1]["stage"] == "expected_direct_effect"
    assert not _outputs(out, "residual_attribution").exists()
    assert not _outputs(out, "secondary_evidence_integration").exists()


def test_until_transcript_targetability_ratio_still_stops_at_ratio(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG, output_dir=out, until_stage="transcript_targetability_ratio"
    )
    assert rows[-1]["stage"] == "transcript_targetability_ratio"
    assert not _outputs(out, "expected_direct_effect").exists()
    assert not _outputs(out, "residual_attribution").exists()
    assert not _outputs(out, "secondary_evidence_integration").exists()


def test_secondary_evidence_integration_resume_reuses_committed_stage(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(config_path=CONFIG, output_dir=out)
    second = run_staged_analysis(config_path=CONFIG, output_dir=out)
    assert second[-1]["stage"] == "secondary_evidence_integration"
    assert second[-1]["action"] == "reuse"
