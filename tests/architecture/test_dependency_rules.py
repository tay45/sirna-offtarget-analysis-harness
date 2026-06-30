from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src/sirna_offtarget"


def test_scientific_modules_do_not_import_cli_or_reporting() -> None:
    forbidden = ("sirna_offtarget.cli", "sirna_offtarget.reporting")
    for package in ("sequence", "expression", "isoform", "pathway", "scoring"):
        for path in (ROOT / package).glob("*.py"):
            text = path.read_text()
            assert not any(item in text for item in forbidden), path
