from __future__ import annotations

from pathlib import Path

import pytest

from sirna_offtarget.pathway.membership.exceptions import AnnotationMembershipError
from sirna_offtarget.pathway.membership.go import build_annotation_membership_snapshot as go_build
from sirna_offtarget.pathway.membership.loaders import (
    build_annotation_membership_snapshot,
    load_verified_memberships,
    verify_membership_cache,
)
from sirna_offtarget.pathway.membership.normalization import to_enrichment_memberships
from sirna_offtarget.pathway.membership.panther import (
    build_annotation_membership_snapshot as panther_build,
)
from sirna_offtarget.pathway.membership.reactome import (
    build_annotation_membership_snapshot as reactome_build,
)
from sirna_offtarget.pathway.membership.verification import verify_membership_cache as verify_api


def test_membership_loader_rejects_missing_inputs(tmp_path: Path) -> None:
    with pytest.raises(AnnotationMembershipError):
        build_annotation_membership_snapshot(
            cache_dir=tmp_path,
            provider="reactome",
            input_files=[],
            organism="human",
        )


def test_membership_verification_reports_missing_files(tmp_path: Path) -> None:
    snapshot = tmp_path / "reactome" / "broken"
    snapshot.mkdir(parents=True)
    (snapshot / "annotation_membership_manifest.json").write_text(
        '{"schema_version": "bad", "normalized_checksums": {}, "completeness_status": "bad"}\n'
    )
    errors = verify_membership_cache(tmp_path)
    assert any("unsupported annotation membership schema" in error for error in errors)
    assert any("missing annotation memberships" in error for error in errors)
    assert any("not verified" in error for error in errors)
    assert verify_api(tmp_path) == errors


def test_membership_wrapper_modules_are_importable(tmp_path: Path) -> None:
    resource = tmp_path / "m.tsv"
    resource.write_text(
        "term_id\tterm_name\tmember_entity_id\tcanonical_gene_ids\tcompleteness_status\n"
        "T\tTerm\tgene:A\tA\tcomplete\n"
    )
    for builder, provider in [
        (reactome_build, "reactome"),
        (panther_build, "panther"),
        (go_build, "go"),
    ]:
        builder(
            cache_dir=tmp_path / provider,
            provider=provider,
            input_files=[resource],
            organism="human",
        )
    records = load_verified_memberships(tmp_path / "reactome")
    assert to_enrichment_memberships(records)
