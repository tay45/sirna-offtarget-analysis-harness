from __future__ import annotations

from pathlib import Path

from sirna_offtarget.models import Direction
from sirna_offtarget.pathway.enrichment.background import build_background_universe
from sirna_offtarget.pathway.enrichment.gene_sets import build_gene_sets
from sirna_offtarget.pathway.enrichment.local_ora import run_local_ora
from sirna_offtarget.pathway.membership import (
    build_annotation_membership_snapshot,
    load_verified_memberships,
    to_enrichment_memberships,
)
from tests.unit.pathway.enrichment.test_gene_set_builder import _expr

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "tests/fixtures/annotation_memberships.tsv"


def test_local_ora_consumes_verified_complete_membership_snapshot(tmp_path: Path) -> None:
    build_annotation_membership_snapshot(
        cache_dir=tmp_path,
        provider="reactome",
        input_files=[FIXTURE],
        organism="human",
        annotation_source="REACTOME_PATHWAY",
        snapshot_id="reactome-human-test",
        provider_release="release-test",
    )
    expression = {
        "A": _expr("A", Direction.UP, 1.0, 0.01),
        "B": _expr("B", Direction.UP, 0.9, 0.01),
        "C": _expr("C", Direction.UNCHANGED, 0.0, 0.8),
        "D": _expr("D", Direction.DOWN, -0.9, 0.01),
    }
    memberships = to_enrichment_memberships(load_verified_memberships(tmp_path))
    gene_sets = build_gene_sets(expression)
    background = build_background_universe(expression, memberships, mode="all_tested_genes")
    results = run_local_ora(gene_sets, background, memberships)
    assert results
    assert all(result.annotation_membership_completeness == "complete" for result in results)
    assert {result.term_id for result in results} == {"R-HSA-1"}
