from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis


def test_unchanged_resume_records_reuse_event_without_attempt(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(config_path=Path("examples/synthetic/config.yaml"), output_dir=out)
    before = len(list(out.glob("stages/*/attempts/attempt_*/stage_manifest.json")))
    run_staged_analysis(config_path=Path("examples/synthetic/config.yaml"), output_dir=out)
    after = len(list(out.glob("stages/*/attempts/attempt_*/stage_manifest.json")))
    assert after == before
    assert all(path.exists() for path in out.glob("stages/*/reuse_events.jsonl"))
