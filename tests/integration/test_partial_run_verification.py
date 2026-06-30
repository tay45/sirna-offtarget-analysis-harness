from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis, verify_run
from sirna_offtarget.execution.hashing import load_json


def test_partial_run_verification(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(
        config_path=Path("examples/synthetic/config.yaml"),
        output_dir=out,
        until_stage="expression_analysis",
    )
    assert verify_run(out) == []
    assert load_json(out / "run_status.json")["status"] == "partially_completed"
