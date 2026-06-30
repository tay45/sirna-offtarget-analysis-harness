from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src/sirna_offtarget"


def test_core_does_not_import_concrete_external_engines() -> None:
    forbidden = ("RNAfold", "viennarna", "bowtie", "blast")
    for path in ROOT.rglob("*.py"):
        text = path.read_text().lower()
        assert not any(item.lower() in text for item in forbidden), path
