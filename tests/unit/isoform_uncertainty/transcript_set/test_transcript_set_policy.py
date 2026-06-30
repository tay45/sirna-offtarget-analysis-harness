from __future__ import annotations

from sirna_offtarget.isoform_uncertainty.contracts import TranscriptSetPolicyV1
from sirna_offtarget.isoform_uncertainty.core import (
    assign_isoform_uncertainty_for_gene,
    validate_annotation_snapshot,
)
from tests.unit.isoform_uncertainty.conftest import tx


def _assign(records, snapshot, policy):
    return assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=records,
        policy=policy,
    )


def test_gene_transcript_relationship_and_version_preserved(snapshot, policy) -> None:
    gene, weights, _ = _assign([tx("ENST1", version="7")], snapshot, policy)
    assert gene.annotated_transcript_count == 1
    assert weights[0].original_transcript_id == "ENST1.7"
    assert weights[0].transcript_version == "7"


def test_biotype_preserved(snapshot, policy) -> None:
    _gene, weights, _ = _assign([tx("ENST1", biotype="lncRNA")], snapshot, policy)
    assert weights[0].transcript_biotype == "lncRNA"


def test_deprecated_transcript_policy(snapshot, policy) -> None:
    gene, weights, exclusions = _assign([tx("ENST1", deprecated=True)], snapshot, policy)
    assert gene.eligible_transcript_count == 0
    assert weights == []
    assert exclusions[0].exclusion_reason == "deprecated_transcript"


def test_missing_sequence_reference_policy(snapshot, policy) -> None:
    _gene, _weights, exclusions = _assign([tx("ENST1", sequence=None)], snapshot, policy)
    assert exclusions[0].exclusion_reason == "missing_sequence_reference"


def test_alternative_contig_policy(snapshot, policy) -> None:
    _gene, _weights, exclusions = _assign([tx("ENST1", alternative_contig=True)], snapshot, policy)
    assert exclusions[0].exclusion_reason == "alternative_contig"


def test_unresolved_and_ambiguous_transcript_preserved(snapshot, policy) -> None:
    unresolved = tx("ENST1", canonical_transcript_id=None)
    unresolved = unresolved.model_copy(update={"canonical_transcript_id": None})
    ambiguous = tx("ENST2", ambiguous=True)
    _gene, _weights, exclusions = _assign([unresolved, ambiguous], snapshot, policy)
    assert {item.exclusion_reason for item in exclusions} == {
        "unresolved_transcript_mapping",
        "ambiguous_transcript_mapping",
    }


def test_organism_and_assembly_mismatch_rejected(snapshot, policy) -> None:
    _gene, _weights, exclusions = _assign(
        [tx("ENST1", organism="mouse"), tx("ENST2", assembly="GRCm39")],
        snapshot,
        policy,
    )
    assert {item.exclusion_reason for item in exclusions} == {
        "organism_mismatch",
        "assembly_mismatch",
    }


def test_policy_change_changes_fingerprint() -> None:
    first = TranscriptSetPolicyV1()
    second = TranscriptSetPolicyV1(allow_deprecated_transcripts=True)
    assert first.fingerprint != second.fingerprint


def test_annotation_validation_requires_verified_snapshot(snapshot) -> None:
    unverified = snapshot.model_copy(update={"verification_status": "unverified"})
    validation = validate_annotation_snapshot(unverified, [tx("ENST1")])
    assert "annotation snapshot is not verified" in validation.fatal_errors
