from __future__ import annotations

from sirna_offtarget.models import Direction, ExpressionResult
from sirna_offtarget.pathway.enrichment.gene_sets import build_gene_sets


def test_gene_set_builder_separates_up_down_and_exclusions() -> None:
    sets = build_gene_sets(
        {
            "UP1": _expr("UP1", Direction.UP, 1.2, 0.01),
            "DOWN1": _expr("DOWN1", Direction.DOWN, -1.1, 0.02),
            "LOW": _expr("LOW", Direction.UP, 2.0, 0.01, low_count=True),
            "UNCHANGED": _expr("UNCHANGED", Direction.UNCHANGED, 0.1, 0.9),
        },
        intended_target_gene="DOWN1",
    )
    by_id = {gene_set.gene_set_id: gene_set for gene_set in sets}
    assert by_id["significant_upregulated"].genes == ("UP1",)
    assert by_id["significant_downregulated"].genes == ("DOWN1",)
    assert by_id["all_tested_changed"].genes == ("DOWN1", "UP1")
    assert by_id["intended_target_related"].genes == ("DOWN1",)
    assert by_id["low_count_excluded"].genes == ("LOW",)
    assert by_id["significant_upregulated"].exclusion_reasons["LOW"] == "low_count_excluded"


def _expr(
    gene: str,
    direction: Direction,
    lfc: float,
    padj: float,
    *,
    low_count: bool = False,
) -> ExpressionResult:
    return ExpressionResult(
        gene=gene,
        baseline_expression=1.0 if low_count else 20.0,
        normalized_control_expression=10.0,
        normalized_treated_expression=10.0 * (2**lfc),
        log2_fold_change=lfc,
        shrunken_log2_fold_change=lfc,
        adjusted_p_value=padj,
        replicate_consistency=1.0,
        direction=direction,
        low_count_flag=low_count,
    )
