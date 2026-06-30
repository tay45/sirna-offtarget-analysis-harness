from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_public_example_contains_unresolved_case() -> None:
    table = (ROOT / "examples/portfolio/portfolio_result_summary.tsv").read_text()
    annotation = (ROOT / "examples/portfolio/annotation.gtf").read_text()
    sequence_records = (
        ROOT / "examples/portfolio/sequence_cache/portfolio-v1/transcript_sequences.jsonl"
    ).read_text()
    assert "SEQUENCE_MISSING" in table
    assert "ratio unavailable because transcript sequence was unavailable" in table
    assert "sequence_missing_tx1" in annotation
    assert "sequence_missing_tx1" not in sequence_records
