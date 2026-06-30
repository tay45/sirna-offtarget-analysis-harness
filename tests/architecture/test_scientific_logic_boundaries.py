from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src/sirna_offtarget"


def test_cli_contains_no_scientific_formula_literals() -> None:
    text = (ROOT / "cli.py").read_text()
    assert "log2" not in text
    assert "mismatch" not in text
    assert "fold_change" not in text


def test_reporting_does_not_import_scoring_implementations() -> None:
    package = ".".join(("sirna_offtarget", "scoring"))
    for path in (ROOT / "reporting").glob("*.py"):
        text = path.read_text()
        assert f"{package}.direct_score" not in text
        assert f"{package}.secondary_score" not in text
