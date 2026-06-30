from pathlib import Path

from tests.portfolio.integrity_helpers import EXPECTED_RATIO_STAGES, run_portfolio


def test_until_ratio_executes_only_transitive_prerequisites(tmp_path: Path) -> None:
    assert run_portfolio(tmp_path / "run") == EXPECTED_RATIO_STAGES
