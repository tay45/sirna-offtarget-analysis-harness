from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis

ROOT = Path(__file__).resolve().parents[2]


def test_portfolio_example_runs(tmp_path: Path) -> None:
    rows = run_staged_analysis(
        config_path=ROOT / "examples/portfolio/config.yaml",
        output_dir=tmp_path / "run",
        until_stage="transcript_targetability_ratio",
    )
    assert rows[-1]["stage"] == "transcript_targetability_ratio"
    assert rows[-1]["status"] == "completed"
