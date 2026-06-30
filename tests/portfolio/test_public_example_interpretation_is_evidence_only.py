from tests.portfolio.integrity_helpers import PORTFOLIO, PROHIBITED_TEXT


def test_public_example_interpretation_is_evidence_only() -> None:
    text = (PORTFOLIO / "portfolio_result_summary.md").read_text().lower()
    assert not [phrase for phrase in PROHIBITED_TEXT if phrase in text]
    assert "cleavage-compatible evidence" in text
