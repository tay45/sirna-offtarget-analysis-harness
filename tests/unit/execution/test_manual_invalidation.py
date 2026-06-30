from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.api import (
    invalidate_run,
    list_invalidations,
    plan_run,
    run_staged_analysis,
)


def test_manual_invalidation_is_applied_once(tmp_path: Path) -> None:
    out = tmp_path / "run"
    config = Path("examples/synthetic/config.yaml")
    run_staged_analysis(config_path=config, output_dir=out)
    request = invalidate_run(out, "expression_analysis", True, "test request")
    assert list_invalidations(out)[0]["request_id"] == request["request_id"]
    plan = plan_run(config_path=config, output_dir=out)
    assert any(
        row["stage"] == "expression_analysis" and row["action"] == "invalidate" for row in plan
    )
    run_staged_analysis(config_path=config, output_dir=out)
    assert list_invalidations(out)[0]["status"] == "consumed"
    later_plan = plan_run(config_path=config, output_dir=out)
    assert all(row["action"] == "reuse" for row in later_plan)
