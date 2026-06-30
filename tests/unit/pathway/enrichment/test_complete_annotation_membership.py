from __future__ import annotations

from sirna_offtarget.models import Direction
from sirna_offtarget.pathway.enrichment.background import build_background_universe
from sirna_offtarget.pathway.enrichment.gene_sets import build_gene_sets
from sirna_offtarget.pathway.enrichment.local_ora import (
    build_memberships_from_provider_results,
    run_local_ora,
)
from sirna_offtarget.pathway.enrichment.models import PathwayMembershipRecordV1
from tests.unit.pathway.enrichment.test_gene_set_builder import _expr


def test_hit_only_membership_is_rejected_for_production_local_ora() -> None:
    expression = {
        "A": _expr("A", Direction.UP, 1.0, 0.01),
        "B": _expr("B", Direction.UP, 1.0, 0.01),
        "C": _expr("C", Direction.UNCHANGED, 0.0, 0.9),
    }
    memberships = build_memberships_from_provider_results(
        [
            {
                "provider": "reactome",
                "annotation_source": "REACTOME_PATHWAY",
                "term_id": "R-HSA-1",
                "term_name": "Submitted hit only",
                "matched_genes": ("A", "B"),
            }
        ]
    )
    gene_sets = build_gene_sets(expression)
    background = build_background_universe(expression, memberships, mode="all_tested_genes")
    assert run_local_ora(gene_sets, background, memberships) == []


def test_complete_membership_is_eligible_for_local_ora() -> None:
    expression = {
        "A": _expr("A", Direction.UP, 1.0, 0.01),
        "B": _expr("B", Direction.UP, 1.0, 0.01),
        "C": _expr("C", Direction.UNCHANGED, 0.0, 0.9),
    }
    memberships = [
        PathwayMembershipRecordV1(
            provider="reactome",
            annotation_source="REACTOME_PATHWAY",
            term_id="R-HSA-1",
            term_name="Complete term",
            member_entity_id=f"gene:{gene}",
            member_gene_id=gene,
            organism="human",
            hierarchy_parent_ids=(),
            evidence_type="curated_membership",
            provider_version="release1",
            snapshot_id="complete-snapshot",
        )
        for gene in ("A", "B", "C")
    ]
    gene_sets = build_gene_sets(expression)
    background = build_background_universe(expression, memberships, mode="all_tested_genes")
    results = run_local_ora(gene_sets, background, memberships)
    assert results
    assert {result.annotation_membership_completeness for result in results} == {"complete"}
