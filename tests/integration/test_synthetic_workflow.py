from pathlib import Path

from click.testing import CliRunner

from sirna_offtarget.cli import main

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "examples/synthetic/config.yaml"


def test_complete_synthetic_workflow(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    for args in (
        ["validate-config", "--config", str(CONFIG)],
        ["run", "--config", str(CONFIG), "--output-dir", str(out)],
        ["report", "--run-dir", str(out)],
    ):
        result = runner.invoke(main, args)
        assert result.exit_code == 0, result.output
    expected = (
        out
        / "stages"
        / "11_secondary_evidence_integration"
        / "attempts"
        / "attempt_001"
        / "committed"
        / "outputs"
        / "gene_secondary_evidence_integration_v1.tsv"
    )
    assert expected.exists()
    assert not (out / "complete_results.json").exists()
    assert "_".join(("final", "classification")) not in expected.read_text()
