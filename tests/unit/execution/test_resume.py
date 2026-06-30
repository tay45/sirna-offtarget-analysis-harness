from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.api import resume_run, run_staged_analysis, status_run


def test_resume_reuses_valid_completed_stages(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(
        config_path=Path("examples/synthetic/config.yaml"),
        output_dir=out,
        until_stage="sequence_analysis",
    )
    rows = resume_run(out)
    assert any(row["stage"] == "sequence_analysis" and row["action"] == "reuse" for row in rows)
    assert status_run(out)[-1]["status"] == "completed"
