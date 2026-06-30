from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis, stage_attempts


def test_reuse_does_not_create_execution_attempt(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(config_path=Path("examples/synthetic/config.yaml"), output_dir=out)
    before = stage_attempts(out, "sequence_analysis")
    run_staged_analysis(config_path=Path("examples/synthetic/config.yaml"), output_dir=out)
    after = stage_attempts(out, "sequence_analysis")
    assert len(after) == len(before)
    assert (out / "stages/04_sequence_analysis/reuse_events.jsonl").exists()
