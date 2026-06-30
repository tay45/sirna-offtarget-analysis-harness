from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT / "examples" / "portfolio"
OUTPUTS = (
    ROOT
    / "work"
    / "quickstart_check2"
    / "stages"
    / "08_transcript_targetability_ratio"
    / "attempts"
    / "attempt_001"
    / "committed"
    / "outputs"
)
TARGETABILITY_OUTPUTS = (
    ROOT
    / "work"
    / "quickstart_check2"
    / "stages"
    / "07_transcript_targetability"
    / "attempts"
    / "attempt_001"
    / "committed"
    / "outputs"
)

COLUMNS = [
    "Gene",
    "Eligible transcripts N",
    "Cleavage-compatible transcripts M",
    "M/N",
    "Exact-match transcripts",
    "Seed-only transcripts",
    "Unresolved transcripts",
    "Sequence status",
    "Ratio status",
    "Evidence interpretation",
]


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _interpret(row: dict[str, str], exact_count: int) -> str:
    n = int(row["n_total_eligible_transcripts"])
    m = row["m_targetable_transcripts"]
    unresolved = int(row["unresolved_transcript_count"])
    seed_only = int(row["seed_only_transcript_count"])
    if unresolved:
        return "ratio unavailable because transcript sequence was unavailable"
    if m and int(m) == n:
        return "all eligible transcripts contain cleavage-compatible evidence"
    if m and int(m) > 0:
        return "a subset of eligible transcripts contains cleavage-compatible evidence"
    if seed_only and exact_count == 0:
        return "seed-only evidence was preserved separately"
    return "no cleavage-compatible evidence was identified"


def main() -> None:
    ratios = _read_tsv(OUTPUTS / "gene_transcript_targetability_ratios_v1.tsv")
    evidence = _read_tsv(TARGETABILITY_OUTPUTS / "transcript_targetability_evidence_v1.tsv")
    exact_by_gene: dict[str, int] = {}
    for record in evidence:
        exact_by_gene.setdefault(record["canonical_gene_id"], 0)
        if int(record["exact_site_count"]):
            exact_by_gene[record["canonical_gene_id"]] += 1

    rows: list[dict[str, str]] = []
    for row in sorted(ratios, key=lambda item: item["canonical_gene_id"]):
        gene = row["canonical_gene_id"]
        exact_count = exact_by_gene.get(gene, 0)
        unresolved = int(row["unresolved_transcript_count"])
        rows.append(
            {
                "Gene": gene,
                "Eligible transcripts N": row["n_total_eligible_transcripts"],
                "Cleavage-compatible transcripts M": row["m_targetable_transcripts"],
                "M/N": row["ratio_m_over_n"],
                "Exact-match transcripts": str(exact_count),
                "Seed-only transcripts": row["seed_only_transcript_count"],
                "Unresolved transcripts": str(unresolved),
                "Sequence status": "unavailable" if unresolved else "available",
                "Ratio status": row["ratio_status"],
                "Evidence interpretation": _interpret(row, exact_count),
            }
        )

    tsv_path = PORTFOLIO / "portfolio_result_summary.tsv"
    with tsv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    md_path = PORTFOLIO / "portfolio_result_summary.md"
    with md_path.open("w") as handle:
        handle.write("| " + " | ".join(COLUMNS) + " |\n")
        handle.write("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |\n")
        for row in rows:
            handle.write("| " + " | ".join(row[column] for column in COLUMNS) + " |\n")


if __name__ == "__main__":
    main()
