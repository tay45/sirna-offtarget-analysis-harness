from __future__ import annotations

from pathlib import Path

import pytest

from sirna_offtarget.identifiers.exceptions import IdentifierSnapshotError
from sirna_offtarget.identifiers.resolver_v2 import IdentifierResolverV2
from sirna_offtarget.identifiers.snapshots import write_identifier_snapshot


def test_identifier_resolver_v2_indexes_aliases_and_excludes_unresolved(tmp_path: Path) -> None:
    snapshot = write_identifier_snapshot(tmp_path, "human")
    resolver = IdentifierResolverV2(snapshot, "human")

    alias = resolver.resolve_one("P53", expected_entity_type="gene")
    missing = resolver.resolve_one("NOT_A_GENE", expected_entity_type="gene")

    assert alias.ambiguity_status == "unambiguous"
    assert alias.canonical_gene_ids == ("HGNC:11998",)
    assert missing.ambiguity_status == "unresolved"
    assert missing.canonical_gene_ids == ()
    assert missing.exclusion_status == "excluded"


def test_identifier_resolver_v2_rejects_organism_mismatch(tmp_path: Path) -> None:
    snapshot = write_identifier_snapshot(tmp_path, "human")
    with pytest.raises(IdentifierSnapshotError, match="organism mismatch"):
        IdentifierResolverV2(snapshot, "mouse")


def test_identifier_resolver_v2_ambiguous_default_excludes(tmp_path: Path) -> None:
    snapshot = write_identifier_snapshot(tmp_path, "human")
    resolver = IdentifierResolverV2(snapshot, "human")
    result = resolver.resolve_expression_gene("OLD1")
    assert result.ambiguity_status == "ambiguous"
    assert result.resolved_entity_id is None
    assert result.exclusion_status == "excluded"
