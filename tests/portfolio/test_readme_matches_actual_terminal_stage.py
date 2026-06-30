from tests.portfolio.integrity_helpers import ROOT


def test_readme_matches_actual_terminal_stage() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "transcript_targetability_ratio" in readme
    assert "final classification remain planned" in readme
