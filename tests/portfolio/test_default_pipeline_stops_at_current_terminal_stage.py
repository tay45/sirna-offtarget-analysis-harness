from pathlib import Path

from tests.portfolio.integrity_helpers import EXPECTED_CURRENT_STAGES, run_portfolio


def test_default_pipeline_stops_at_current_terminal_stage(tmp_path: Path) -> None:
    assert run_portfolio(tmp_path / "run", until_stage=None) == EXPECTED_CURRENT_STAGES
