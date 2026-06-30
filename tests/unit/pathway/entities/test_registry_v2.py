from __future__ import annotations

from sirna_offtarget.identifiers.resolver_v2 import IdentifierResolutionRecordV2
from sirna_offtarget.pathway.entities import BiologicalEntityRegistryV2


def test_registry_registers_resolved_gene_and_unresolved_unknown() -> None:
    registry = BiologicalEntityRegistryV2("human", "snapshot-1")
    resolved = IdentifierResolutionRecordV2(
        resolution_id="r1",
        input_identifier="TP53",
        input_namespace="approved_symbol",
        detected_type="gene_symbol",
        normalized_input="TP53",
        expected_entity_type="gene",
        resolved_entity_id="gene:TP53",
        canonical_gene_ids=("TP53",),
        approved_symbol="TP53",
        organism="human",
        mapping_source="fixture",
        mapping_record_ids=("TP53",),
        identifier_snapshot_id="snapshot-1",
        mapping_confidence=0.92,
        ambiguity_status="unambiguous",
        ambiguity_group_id=None,
        candidate_mappings=(),
        deprecated_status="current",
        organism_match=True,
        exclusion_status="included",
        exclusion_reason=None,
        warnings=(),
    )
    unresolved = IdentifierResolutionRecordV2(
        **{
            **resolved.asdict(),
            "resolution_id": "r2",
            "input_identifier": "CHEBI:1",
            "resolved_entity_id": None,
            "canonical_gene_ids": (),
            "approved_symbol": None,
            "mapping_confidence": 0.0,
            "ambiguity_status": "unresolved",
            "exclusion_status": "excluded",
        }
    )
    gene = registry.register_from_resolution(resolved, provider="signor")
    unknown = registry.register_from_resolution(unresolved, provider="reactome")

    assert gene.entity_type == "gene"
    assert gene.mapping_confidence == 0.92
    assert unknown.entity_type == "unknown"
    assert unknown.canonical_gene_ids == ()
    assert registry.unsupported_rows()[0]["entity_id"] == unknown.entity_id


def test_registry_preserves_non_gene_entities_and_expansion_policy() -> None:
    registry = BiologicalEntityRegistryV2("human", "snapshot-1")
    complex_entity = registry.register_complex("Reactome:Complex1", provider="reactome")
    protein = registry.register_protein("P04637", provider="uniprot")
    registry.add_membership(complex_entity.entity_id, protein.entity_id)

    assert complex_entity.entity_type == "complex"
    assert registry.expand_for_policy(complex_entity.entity_id, "no_expansion") == (
        complex_entity.entity_id,
    )
    assert registry.expand_for_policy(complex_entity.entity_id, "expand_resolvable_members") == (
        protein.entity_id,
    )


def test_registry_merges_duplicate_provenance_and_rejects_unknown_policy() -> None:
    registry = BiologicalEntityRegistryV2("human", "snapshot-1")

    first = registry.register_gene(
        "TP53",
        source_identifier="tp53",
        provider="signor",
        provider_record_id="S1",
    )
    merged = registry.register_gene(
        "TP53",
        source_identifier="P04637",
        provider="reactome",
        provider_record_id="R1",
    )

    assert first.entity_id == merged.entity_id
    assert merged.source_identifiers == ("P04637", "tp53")
    assert merged.provider_sources == ("reactome", "signor")
    assert merged.provider_record_ids == ("R1", "S1")
    assert registry.get(merged.entity_id) == merged

    try:
        registry.expand_for_policy(merged.entity_id, "explode_everything")
    except ValueError as error:
        assert "unsupported entity expansion policy" in str(error)
    else:  # pragma: no cover - defensive assertion shape
        raise AssertionError("unsupported expansion policy should fail")


def test_registry_registers_supported_non_gene_entity_types() -> None:
    registry = BiologicalEntityRegistryV2("human", "snapshot-1")
    entities = [
        registry.register_transcript("ENST0001"),
        registry.register_protein_family("PFAM:kinase"),
        registry.register_entity_set("Reactome:set"),
        registry.register_reaction("Reactome:reaction"),
        registry.register_pathway("Reactome:pathway"),
        registry.register_small_molecule("CHEBI:1"),
        registry.register_phenotype("HP:1"),
    ]

    assert {entity.entity_type for entity in entities} == {
        "transcript",
        "protein_family",
        "entity_set",
        "reaction",
        "pathway",
        "small_molecule",
        "phenotype",
    }
    assert registry.to_rows()
