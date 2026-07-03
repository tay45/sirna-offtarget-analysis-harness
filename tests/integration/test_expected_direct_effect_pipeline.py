from __future__ import annotations

import json
from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis, verify_run
from sirna_offtarget.execution.dag import stage_index
from sirna_offtarget.expected_direct_effect.artifacts import (
    verify_expected_direct_effect_outputs,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "examples/portfolio/config.yaml"


def _stage_outputs(out: Path) -> Path:
    return (
        out
        / "stages"
        / f"{stage_index('expected_direct_effect'):02d}_expected_direct_effect"
        / "attempts"
        / "attempt_001"
        / "committed"
        / "outputs"
    )


def test_expected_direct_effect_pipeline_outputs_verify(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG,
        output_dir=out,
        until_stage="expected_direct_effect",
    )
    assert rows[-1]["stage"] == "expected_direct_effect"
    outputs = _stage_outputs(out)
    assert verify_expected_direct_effect_outputs(outputs)["passed"]
    assert verify_run(out) == []
    summary = json.loads((outputs / "expected_direct_effect_summary_v1.json").read_text())
    assert summary["pathway_evidence_used"] is False
    assert summary["classification_performed"] is False
    records = [
        json.loads(line)
        for line in (outputs / "gene_expected_direct_effects_v1.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert records
    assert all(
        record["residual_interpretation"] == "unresolved_residual_only" for record in records
    )
    assert all("expected_direct_effect_log2fc" in record for record in records)
    assert all("observed_vs_expected_difference" not in record for record in records)


def test_expected_direct_effect_resume_reuses_committed_stage(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(config_path=CONFIG, output_dir=out, until_stage="expected_direct_effect")
    second = run_staged_analysis(
        config_path=CONFIG,
        output_dir=out,
        until_stage="expected_direct_effect",
    )
    assert second[-1]["stage"] == "expected_direct_effect"
    assert second[-1]["action"] == "reuse"
