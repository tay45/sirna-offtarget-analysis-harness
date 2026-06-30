from __future__ import annotations

import pytest

from sirna_offtarget.pathway.semantics import (
    BiologicalEntityRecordV2,
    ProviderEdgeEvidenceRecordV2,
    calculate_evidence_quality_v2,
    calculate_path_confidence_v2,
    classify_contextual_conflict,
)


def test_biological_entity_v2_preserves_non_gene_types() -> None:
    with pytest.raises(ValueError):
        BiologicalEntityRecordV2(
            entity_id="weird:1",
            entity_type="gene_or_gene_product",
            display_name="bad",
            canonical_identifier="bad",
            organism="human",
            source_identifiers=(),
            canonical_gene_ids=(),
            member_entity_ids=(),
            entity_set_semantics="none",
            identifier_snapshot_id="ids",
            mapping_confidence=1.0,
            ambiguity_status="unambiguous",
            provider_sources=(),
            provider_record_ids=(),
            compartments=(),
            contexts=(),
        )
    with pytest.raises(ValueError):
        BiologicalEntityRecordV2(
            entity_id="small:1",
            entity_type="small_molecule",
            display_name="ATP",
            canonical_identifier="CHEBI:15422",
            organism="human",
            source_identifiers=("CHEBI:15422",),
            canonical_gene_ids=("ATP",),
            member_entity_ids=(),
            entity_set_semantics="none",
            identifier_snapshot_id="ids",
            mapping_confidence=1.0,
            ambiguity_status="unambiguous",
            provider_sources=("reactome",),
            provider_record_ids=("r1",),
            compartments=(),
            contexts=(),
        )


def test_evidence_quality_caps_unsigned_fi_only() -> None:
    evidence = ProviderEdgeEvidenceRecordV2(
        evidence_id="e1",
        source_entity_id="gene:A",
        target_entity_id="gene:B",
        source_resolution_id="resolution:A",
        target_resolution_id="resolution:B",
        source_entity_type="gene",
        target_entity_type="gene",
        directed=False,
        sign="unsigned",
        relation_type="functional_interaction",
        mechanism="",
        directness="indirect",
        functional_only=True,
        contextual_only=False,
        causal_eligible=False,
        original_provider="reactome_fi",
        access_provider="reactome_fi",
        original_database="ReactomeFI",
        provider_record_id="fi1",
        references=("PMID:1",),
        organism="human",
        cell_type=None,
        tissue=None,
        compartment=None,
        experimental_system=None,
        disease_state=None,
        predicted_only=False,
        curated_status="curated",
        identifier_snapshot_id="ids",
        provider_snapshot_id="snap",
        provider_version="release",
        normalization_version="provider-evidence-v2",
    )
    quality = calculate_evidence_quality_v2(evidence)
    assert quality.final_level in {"low", "contextual", "insufficient"}
    assert "missing_direction_or_sign_low_cap" in quality.cap_reasons


def test_evidence_quality_caps_prediction_and_unknown_entity() -> None:
    evidence = ProviderEdgeEvidenceRecordV2(
        evidence_id="e2",
        source_entity_id="unknown:X",
        target_entity_id="gene:B",
        source_resolution_id="resolution:X",
        target_resolution_id="resolution:B",
        source_entity_type="unknown",
        target_entity_type="gene",
        directed=True,
        sign="positive",
        relation_type="regulation",
        mechanism="explicit",
        directness="direct",
        functional_only=False,
        contextual_only=False,
        causal_eligible=True,
        original_provider="reactome",
        access_provider="reactome",
        original_database="Reactome",
        provider_record_id="r1",
        references=(),
        organism="human",
        cell_type="cell:A",
        tissue=None,
        compartment=None,
        experimental_system=None,
        disease_state=None,
        predicted_only=True,
        curated_status="curated",
        identifier_snapshot_id="ids",
        provider_snapshot_id="snap",
        provider_version="release",
        normalization_version="provider-evidence-v2",
    )
    quality = calculate_evidence_quality_v2(evidence)
    assert quality.final_level == "insufficient"
    assert "unsupported_entity_insufficient_cap" in quality.cap_reasons
    assert "predicted_only_not_high_cap" in quality.cap_reasons


def test_path_confidence_is_capped_by_bottleneck_edge() -> None:
    confidence = calculate_path_confidence_v2("p1", {"e1": 0.95, "e2": 0.2, "e3": 0.9})
    assert confidence.bottleneck_edge_id == "e2"
    assert confidence.capped_score == 0.2
    assert confidence.capped_score <= confidence.minimum_edge_quality_score


def test_path_confidence_requires_edges() -> None:
    with pytest.raises(ValueError):
        calculate_path_confidence_v2("p0", {})


def test_context_specific_and_unresolved_conflicts_are_distinguished() -> None:
    context_specific = classify_contextual_conflict(
        "c1", "gene:X", ("p1",), ("n1",), ("cell:A",), ("cell:B",)
    )
    unresolved = classify_contextual_conflict("c2", "gene:X", ("p1",), ("n1",), (), ())
    assert context_specific.conflict_class == "context_specific_conflict"
    assert unresolved.conflict_class == "unresolved_context_conflict"


def test_global_context_conflict_has_overlap() -> None:
    conflict = classify_contextual_conflict(
        "c3", "gene:X", ("p1",), ("n1",), ("cell:A",), ("cell:A",)
    )
    assert conflict.conflict_class == "global_sign_conflict"
    assert conflict.context_overlap is True
