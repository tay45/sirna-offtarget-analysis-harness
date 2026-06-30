from pathlib import Path

from click.testing import CliRunner

from scripts.compare_reproducible_outputs import main as compare_main
from sirna_offtarget.cli import main

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "examples/synthetic/config.yaml"


def test_reproducible_outputs(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    left = tmp_path / "left"
    right = tmp_path / "right"
    assert (
        runner.invoke(main, ["run", "--config", str(CONFIG), "--output-dir", str(left)]).exit_code
        == 0
    )
    assert (
        runner.invoke(main, ["run", "--config", str(CONFIG), "--output-dir", str(right)]).exit_code
        == 0
    )
    monkeypatch.setattr("sys.argv", ["compare", str(left), str(right)])
    assert compare_main() == 0
