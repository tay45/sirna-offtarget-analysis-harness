from pathlib import Path

from tests.portfolio.integrity_helpers import run_portfolio


def test_no_downstream_artifacts_after_until_boundary(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_portfolio(out)
    forbidden = (
        "*candidate*",
        "*classification*",
        "*network_visualization*",
        "*final_reporting*",
        "*result_validation*",
    )
    for pattern in forbidden:
        assert not list((out / "stages").glob(pattern))
