from __future__ import annotations

import json
from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis, verify_run
from sirna_offtarget.execution.dag import stage_index
from sirna_offtarget.residual_attribution.artifacts import (
    verify_residual_attribution_outputs,
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


def test_residual_attribution_pipeline_outputs_verify(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(config_path=CONFIG, output_dir=out)
    assert rows[-1]["stage"] == "residual_attribution"
    outputs = _outputs(out, "residual_attribution")
    assert verify_residual_attribution_outputs(outputs)["passed"]
    assert verify_run(out) == []
    summary = json.loads((outputs / "residual_attribution_summary_v1.json").read_text())
    assert summary["classification_performed"] is False
    assert summary["supporting_context_only"] is True
    records = [
        json.loads(line)
        for line in (outputs / "gene_residual_attribution_evidence_v1.jsonl")
        .read_text()
        .splitlines()
        if line.strip()
    ]
    assert records
    assert all(
        record["pathway_support_summary"]["missing_pathway_evidence_interpretation"]
        == "unresolved_not_negative"
        for record in records
    )
    assert all("final_classification" not in record for record in records)


def test_until_expected_direct_effect_still_stops_before_residual_attribution(
    tmp_path: Path,
) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG, output_dir=out, until_stage="expected_direct_effect"
    )
    assert rows[-1]["stage"] == "expected_direct_effect"
    assert not _outputs(out, "residual_attribution").exists()


def test_until_transcript_targetability_ratio_still_stops_at_ratio(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG, output_dir=out, until_stage="transcript_targetability_ratio"
    )
    assert rows[-1]["stage"] == "transcript_targetability_ratio"
    assert not _outputs(out, "expected_direct_effect").exists()
    assert not _outputs(out, "residual_attribution").exists()


def test_residual_attribution_resume_reuses_committed_stage(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(config_path=CONFIG, output_dir=out)
    second = run_staged_analysis(config_path=CONFIG, output_dir=out)
    assert second[-1]["stage"] == "residual_attribution"
    assert second[-1]["action"] == "reuse"
