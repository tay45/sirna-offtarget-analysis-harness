from __future__ import annotations

from sirna_offtarget.pathway.enrichment import overrepresentation_analysis
from sirna_offtarget.pathway.enrichment.statistics import (
    benjamini_hochberg,
    fisher_exact_greater,
    hypergeometric_tail,
)


def test_fisher_and_hypergeometric_tail_match_known_value() -> None:
    assert round(fisher_exact_greater(2, 1, 1, 6), 6) == 0.183333
    assert round(hypergeometric_tail(2, 3, 3, 10), 6) == 0.183333


def test_bh_fdr_monotonic() -> None:
    assert benjamini_hochberg([0.01, 0.04, 0.03]) == [0.03, 0.04, 0.04]


def test_overrepresentation_uses_background_and_up_down_separation() -> None:
    terms = overrepresentation_analysis(
        provider="fixture",
        annotation_source="manual",
        gene_set_category="upregulated",
        expression_direction="up",
        test_genes={"A", "B", "C"},
        pathway_members={"P": {"A", "B", "D"}},
        pathway_names={"P": "Pathway"},
        background_genes={"A", "B", "C", "D", "E", "F"},
        database_release="v",
    )
    assert terms[0].observed_count == 2
    assert terms[0].background_size == 6
    assert terms[0].expression_direction == "up"
