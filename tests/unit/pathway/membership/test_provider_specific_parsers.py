from __future__ import annotations

from pathlib import Path

import pytest

from sirna_offtarget.pathway.membership.exceptions import AnnotationMembershipError
from sirna_offtarget.pathway.membership.go import build_go_membership_snapshot
from sirna_offtarget.pathway.membership.loaders import read_membership_records
from sirna_offtarget.pathway.membership.panther import build_panther_membership_snapshot
from sirna_offtarget.pathway.membership.reactome import build_reactome_membership_snapshot


def test_reactome_membership_parser_requires_reactome_columns(tmp_path: Path) -> None:
    source = tmp_path / "reactome.tsv"
    source.write_text(
        "pathway_id\tpathway_name\treference_entity_id\tgene\n"
        "R-HSA-1\tApoptosis\tREACTOME:TP53\tTP53\n"
    )
    snapshot = build_reactome_membership_snapshot(
        cache_dir=tmp_path / "cache",
        input_files=[source],
        organism="human",
        provider_release="reactome-1",
    )
    records = read_membership_records(snapshot / "annotation_memberships.tsv")
    assert records[0].provider == "reactome"
    assert records[0].term_id == "R-HSA-1"
    assert records[0].canonical_gene_ids == ("TP53",)


def test_panther_and_go_membership_parsers_have_distinct_required_schemas(
    tmp_path: Path,
) -> None:
    panther = tmp_path / "panther.tsv"
    panther.write_text(
        "annotation_dataset\tterm_id\tterm_name\tmapped_gene_id\ttaxon\n"
        "pathway\tP00001\tPANTHER pathway\tTP53\thuman\n"
    )
    go = tmp_path / "go.tsv"
    go.write_text(
        "go_id\tnamespace\tgene\tevidence_code\tassigned_by\n"
        "GO:0006915\tbiological_process\tTP53\tIDA\tUniProt\n"
    )
    assert build_panther_membership_snapshot(
        cache_dir=tmp_path / "cache",
        input_files=[panther],
        organism="human",
        provider_release="panther-1",
    ).exists()
    assert build_go_membership_snapshot(
        cache_dir=tmp_path / "cache",
        input_files=[go],
        organism="human",
        ontology_release="go-1",
    ).exists()


def test_provider_membership_parser_rejects_wrong_schema(tmp_path: Path) -> None:
    source = tmp_path / "wrong.tsv"
    source.write_text("term_id\tgene\nX\tTP53\n")
    with pytest.raises(AnnotationMembershipError, match="missing required columns"):
        build_reactome_membership_snapshot(
            cache_dir=tmp_path / "cache",
            input_files=[source],
            organism="human",
            provider_release="reactome-1",
        )
