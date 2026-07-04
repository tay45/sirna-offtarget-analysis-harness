from __future__ import annotations

import json
from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis, verify_run
from sirna_offtarget.execution.dag import stage_index
from sirna_offtarget.final_evidence_classification.artifacts import (
    verify_final_evidence_classification_outputs,
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


def test_final_evidence_classification_default_pipeline_outputs_verify(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(config_path=CONFIG, output_dir=out)
    assert rows[-1]["stage"] == "final_evidence_classification"
    outputs = _outputs(out, "final_evidence_classification")
    assert verify_final_evidence_classification_outputs(outputs)["passed"]
    assert verify_run(out) == []
    summary = json.loads((outputs / "final_evidence_classification_summary_v1.json").read_text())
    assert summary["classification_labels_are_evidence_based"] is True
    assert summary["clinical_toxicological_or_regulatory_claims_made"] is False
    records = [
        json.loads(line)
        for line in (outputs / "gene_final_evidence_classifications_v1.jsonl")
        .read_text()
        .splitlines()
        if line.strip()
    ]
    assert records
    assert all(record["final_evidence_classification"] for record in records)
    assert all("clinically_validated" not in json.dumps(record) for record in records)


def test_until_secondary_evidence_integration_still_stops_there(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG,
        output_dir=out,
        until_stage="secondary_evidence_integration",
    )
    assert rows[-1]["stage"] == "secondary_evidence_integration"
    assert not _outputs(out, "final_evidence_classification").exists()


def test_until_residual_attribution_still_stops_there(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG, output_dir=out, until_stage="residual_attribution"
    )
    assert rows[-1]["stage"] == "residual_attribution"
    assert not _outputs(out, "secondary_evidence_integration").exists()
    assert not _outputs(out, "final_evidence_classification").exists()


def test_until_expected_direct_effect_still_stops_there(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG,
        output_dir=out,
        until_stage="expected_direct_effect",
    )
    assert rows[-1]["stage"] == "expected_direct_effect"
    assert not _outputs(out, "residual_attribution").exists()
    assert not _outputs(out, "secondary_evidence_integration").exists()
    assert not _outputs(out, "final_evidence_classification").exists()


def test_until_transcript_targetability_ratio_still_stops_at_ratio(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=CONFIG,
        output_dir=out,
        until_stage="transcript_targetability_ratio",
    )
    assert rows[-1]["stage"] == "transcript_targetability_ratio"
    assert not _outputs(out, "expected_direct_effect").exists()
    assert not _outputs(out, "residual_attribution").exists()
    assert not _outputs(out, "secondary_evidence_integration").exists()
    assert not _outputs(out, "final_evidence_classification").exists()


def test_final_evidence_classification_resume_reuses_committed_stage(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(config_path=CONFIG, output_dir=out)
    second = run_staged_analysis(config_path=CONFIG, output_dir=out)
    assert second[-1]["stage"] == "final_evidence_classification"
    assert second[-1]["action"] == "reuse"
