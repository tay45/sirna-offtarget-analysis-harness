from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis

ROOT = Path(__file__).resolve().parents[2]


def test_portfolio_example_stops_at_ratio_stage(tmp_path: Path) -> None:
    out = tmp_path / "run"
    rows = run_staged_analysis(
        config_path=ROOT / "examples/portfolio/config.yaml",
        output_dir=out,
        until_stage="transcript_targetability_ratio",
    )
    assert rows[-1]["stage"] == "transcript_targetability_ratio"
    assert not any((out / "stages").glob("*classification*"))
    assert not any((out / "stages").glob("*final_reporting*"))
