from __future__ import annotations

from sirna_offtarget.models import Direction
from sirna_offtarget.pathway.enrichment.background import build_background_universe
from sirna_offtarget.pathway.enrichment.gene_sets import build_gene_sets
from sirna_offtarget.pathway.enrichment.local_ora import (
    consensus_by_annotation_lineage,
    run_local_ora,
)
from sirna_offtarget.pathway.enrichment.models import PathwayMembershipRecordV1
from tests.unit.pathway.enrichment.test_gene_set_builder import _expr


def test_local_ora_distinguishes_local_from_provider_calculated() -> None:
    expression = {
        "A": _expr("A", Direction.UP, 1.0, 0.01),
        "B": _expr("B", Direction.UP, 0.9, 0.01),
        "C": _expr("C", Direction.DOWN, -0.8, 0.02),
        "D": _expr("D", Direction.UNCHANGED, 0.0, 0.9),
    }
    provider_rows = [
        {
            "provider": "panther",
            "annotation_source": "PANTHER_PATHWAY",
            "term_id": "P1",
            "term_name": "Pathway 1",
            "matched_genes": ("A", "B", "D"),
            "retrieval_snapshot": "snap1",
            "database_version": "release1",
            "organism": "human",
        }
    ]
    memberships = [
        PathwayMembershipRecordV1(
            provider="panther",
            annotation_source="PANTHER_PATHWAY",
            term_id="P1",
            term_name="Pathway 1",
            member_entity_id=f"gene:{gene}",
            member_gene_id=gene,
            organism="human",
            hierarchy_parent_ids=(),
            evidence_type="curated_membership",
            provider_version="release1",
            snapshot_id="snap1",
        )
        for gene in ("A", "B", "D")
    ]
    gene_sets = build_gene_sets(expression)
    background = build_background_universe(expression, memberships, mode="all_tested_genes")
    results = run_local_ora(gene_sets, background, memberships)
    assert results
    assert {result.calculation_mode for result in results} == {
        "locally_calculated_from_provider_annotations"
    }
    assert all(result.background_id == background.background_id for result in results)
    consensus = consensus_by_annotation_lineage(provider_rows, results)
    assert consensus[0]["calculation_modes"] == [
        "locally_calculated_from_provider_annotations",
        "provider_calculated",
    ]
