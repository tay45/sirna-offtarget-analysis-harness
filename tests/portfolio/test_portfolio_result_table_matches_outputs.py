import csv
from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis
from sirna_offtarget.execution.dag import stage_index

ROOT = Path(__file__).resolve().parents[2]


def _ratio_dir(out: Path) -> Path:
    return (
        out
        / "stages"
        / f"{stage_index('transcript_targetability_ratio'):02d}_transcript_targetability_ratio"
        / "attempts/attempt_001/committed/outputs"
    )


def test_portfolio_result_table_matches_outputs(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(
        config_path=ROOT / "examples/portfolio/config.yaml",
        output_dir=out,
        until_stage="transcript_targetability_ratio",
    )
    with (ROOT / "examples/portfolio/portfolio_result_summary.tsv").open(newline="") as handle:
        public_rows = {row["Gene"]: row for row in csv.DictReader(handle, delimiter="\t")}
    with (_ratio_dir(out) / "gene_transcript_targetability_ratios_v1.tsv").open(
        newline=""
    ) as handle:
        ratio_rows = {
            row["canonical_gene_id"]: row for row in csv.DictReader(handle, delimiter="\t")
        }
    assert set(public_rows) == set(ratio_rows)
    for gene, public in public_rows.items():
        ratio = ratio_rows[gene]
        assert public["Eligible transcripts N"] == ratio["n_total_eligible_transcripts"]
        assert public["Cleavage-compatible transcripts M"] == ratio["m_targetable_transcripts"]
        assert public["M/N"] == ratio["ratio_m_over_n"]
        assert public["Seed-only transcripts"] == ratio["seed_only_transcript_count"]
        assert public["Unresolved transcripts"] == ratio["unresolved_transcript_count"]
        assert public["Ratio status"] == ratio["ratio_status"]
