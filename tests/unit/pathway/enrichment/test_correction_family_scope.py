from __future__ import annotations

from sirna_offtarget.models import Direction
from sirna_offtarget.pathway.enrichment.background import build_background_universe
from sirna_offtarget.pathway.enrichment.gene_sets import build_gene_sets
from sirna_offtarget.pathway.enrichment.local_ora import run_local_ora
from sirna_offtarget.pathway.enrichment.models import PathwayMembershipRecordV1
from tests.unit.pathway.enrichment.test_gene_set_builder import _expr


def _membership(term: str, gene: str) -> PathwayMembershipRecordV1:
    return PathwayMembershipRecordV1(
        provider="reactome",
        annotation_source="REACTOME_PATHWAY",
        term_id=term,
        term_name=term,
        member_entity_id=f"gene:{gene}",
        member_gene_id=gene,
        organism="human",
        hierarchy_parent_ids=(),
        evidence_type="curated_membership",
        provider_version="release1",
        snapshot_id="complete-snapshot",
    )


def test_correction_families_do_not_mix_gene_set_directions() -> None:
    expression = {
        "A": _expr("A", Direction.UP, 1.1, 0.01),
        "B": _expr("B", Direction.UP, 1.0, 0.01),
        "C": _expr("C", Direction.DOWN, -1.1, 0.01),
        "D": _expr("D", Direction.DOWN, -1.0, 0.01),
        "E": _expr("E", Direction.UNCHANGED, 0.0, 0.8),
    }
    memberships = [
        _membership("R1", "A"),
        _membership("R1", "B"),
        _membership("R2", "C"),
        _membership("R2", "D"),
    ]
    gene_sets = build_gene_sets(expression)
    background = build_background_universe(expression, memberships, mode="all_tested_genes")
    results = run_local_ora(gene_sets, background, memberships)
    families = {
        result.correction_family_id: result.correction_family_size
        for result in results
        if result.gene_set_id in {"significant_upregulated", "significant_downregulated"}
    }
    assert len(families) >= 2
    assert all("gene_set_id=" in family for family in families)
    assert all(size == 1 for size in families.values())
