from __future__ import annotations

from sirna_offtarget.identifiers import (
    detect_identifier_type,
    normalize_identifier_value,
    resolve_entity,
)
from sirna_offtarget.identifiers.api import resolve_identifier


def test_identifier_type_detection_handles_public_provider_namespaces() -> None:
    assert detect_identifier_type("ENSG00000141510.15") == "ensembl_gene_id"
    assert detect_identifier_type("P04637") == "uniprot_accession"
    assert detect_identifier_type("R-HSA-5673001") == "reactome_stable_id"
    assert detect_identifier_type("SIGNOR-PF24") == "signor_entity_id"
    assert detect_identifier_type("1234") == "entrez_gene_id"
    assert detect_identifier_type("tp53") == "hgnc_symbol"


def test_identifier_normalization_does_not_blindly_uppercase_ensembl_versions() -> None:
    assert normalize_identifier_value("tp53") == "TP53"
    assert normalize_identifier_value("ENSG00000141510.15") == "ENSG00000141510"


def test_alias_resolution_reports_ambiguous_identifiers() -> None:
    resolved = resolve_identifier("OLD1", aliases={"OLD1": ("GENEA", "GENEB")})
    assert resolved.status == "ambiguous"
    assert resolved.mapped_identifier is None
    assert resolved.candidate_mappings == ("GENEA", "GENEB")


def test_resolve_entity_preserves_mapping_provenance() -> None:
    entity = resolve_entity("tp53", organism="human")
    assert entity.canonical_identifier == "TP53"
    assert entity.entity_type == "gene_or_gene_product"
    assert "central_identifier_resolution" in entity.provenance
