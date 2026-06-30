from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_public_example_contains_seed_only_case() -> None:
    table = (ROOT / "examples/portfolio/portfolio_result_summary.tsv").read_text()
    fasta = (ROOT / "examples/portfolio/transcripts.fasta").read_text()
    assert "SEED_ONLY" in table
    assert "\tseed-only evidence was preserved separately" in table
    assert "seed_only_tx1" in fasta
