from tests.portfolio.integrity_helpers import ROOT


def test_readme_matches_actual_terminal_stage() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "secondary_evidence_integration" in readme
    assert "residual_attribution" in readme
    assert "expected_direct_effect" in readme
    assert "final classification" in readme
    assert "remain planned" in readme
