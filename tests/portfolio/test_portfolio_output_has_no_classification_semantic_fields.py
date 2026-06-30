from pathlib import Path

from tests.portfolio.integrity_helpers import run_portfolio, serialized_field_hits


def test_portfolio_output_has_no_classification_semantic_fields(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_portfolio(out)
    assert serialized_field_hits(out) == []
