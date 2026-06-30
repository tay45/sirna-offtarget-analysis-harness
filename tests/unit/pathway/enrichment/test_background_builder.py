from __future__ import annotations

from sirna_offtarget.models import Direction
from sirna_offtarget.pathway.enrichment.background import build_background_universe
from sirna_offtarget.pathway.enrichment.models import PathwayMembershipRecordV1
from tests.unit.pathway.enrichment.test_gene_set_builder import _expr


def test_background_defaults_to_tested_detectable_annotatable_genes() -> None:
    background = build_background_universe(
        {
            "A": _expr("A", Direction.UP, 1.0, 0.01),
            "B": _expr("B", Direction.DOWN, -1.0, 0.01, low_count=True),
            "C": _expr("C", Direction.UP, 1.0, 0.01),
        },
        [_membership("A")],
        min_baseline_expression=5.0,
    )
    assert background.mode == "tested_detectable_annotatable_genes"
    assert background.genes == ("A",)
    assert background.exclusion_counts["below_detectability_threshold"] == 1
    assert background.exclusion_counts["not_provider_annotation_eligible"] == 1


def _membership(gene: str) -> PathwayMembershipRecordV1:
    return PathwayMembershipRecordV1(
        provider="panther",
        annotation_source="PANTHER_PATHWAY",
        term_id="P1",
        term_name="Pathway 1",
        member_entity_id=f"gene:{gene}",
        member_gene_id=gene,
        organism="human",
        hierarchy_parent_ids=(),
        evidence_type="provider_annotation_membership",
        provider_version="fixture",
        snapshot_id="snapshot",
    )
