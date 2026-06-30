from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_states_scientific_purpose() -> None:
    readme = (ROOT / "README.md").read_text()
    assert readme.startswith("# siRNA Off-Target Analysis Harness")
    assert (
        "A reproducible weight-of-evidence framework for distinguishing direct siRNA "
        "off-target effects from downstream secondary expression changes."
    ) in readme
    assert "normalized transcriptomic changes" in readme
    assert "sequence-based transcript targetability" in readme
    assert "isoform uncertainty" in readme
    assert "pathway and mechanistic evidence" in readme
