from __future__ import annotations

import pytest

from sirna_offtarget.isoform_uncertainty.contracts import ExternalTranscriptProportionRecordV1
from sirna_offtarget.isoform_uncertainty.core import (
    assign_isoform_uncertainty_for_gene,
    validate_external_proportions,
)
from tests.unit.isoform_uncertainty.conftest import tx


def prop(transcript: str, value: float, *, gene: str = "HGNC:11998", release: str = "v44"):
    return ExternalTranscriptProportionRecordV1(
        original_gene_id="TP53",
        original_transcript_id=transcript,
        canonical_gene_id=gene,
        canonical_transcript_id=transcript,
        proportion=value,
        sample_or_contrast_scope="treated_vs_control",
        source_method="precomputed_transcript_proportions",
        source_software="external",
        source_software_version="1",
        annotation_release=release,
        organism="human",
        assembly="GRCh38",
        source_file_checksum="sha256:props",
    )


def test_valid_proportions_preserved(snapshot, policy) -> None:
    gene, weights, _ = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1"), tx("ENST2")],
        policy=policy,
        external_proportions=[prop("ENST1", 0.25), prop("ENST2", 0.75)],
    )
    assert gene.isoform_resolution_status == "multiple_transcripts_external_proportions"
    assert [item.weight for item in weights] == [0.25, 0.75]
    assert {item.weight_type for item in weights} == {"external_proportion"}


def test_negative_and_non_numeric_proportions_rejected() -> None:
    with pytest.raises(ValueError):
        prop("ENST1", -0.1)
    with pytest.raises(ValueError):
        ExternalTranscriptProportionRecordV1.model_validate(
            prop("ENST1", 0.1).model_dump() | {"proportion": "bad"}
        )


def test_duplicate_wrong_mapping_and_sum_errors(snapshot, policy) -> None:
    valid, errors, total = validate_external_proportions(
        proportions=[prop("ENST1", 0.4), prop("ENST1", 0.4), prop("ENSTX", 0.1)],
        eligible_transcripts=[tx("ENST1")],
        snapshot=snapshot,
    )
    assert not valid
    assert total == 0.9
    assert "duplicate_gene_transcript_row" in errors
    assert "transcript_not_eligible_for_gene" in errors
    assert "proportion_sum_outside_tolerance" in errors


def test_small_rounding_error_policy(snapshot) -> None:
    valid, errors, _ = validate_external_proportions(
        proportions=[prop("ENST1", 0.3333334), prop("ENST2", 0.6666666)],
        eligible_transcripts=[tx("ENST1"), tx("ENST2")],
        snapshot=snapshot,
        tolerance=1e-5,
    )
    assert valid
    assert errors == ()


def test_renormalization_requires_explicit_policy(snapshot) -> None:
    valid, errors, _ = validate_external_proportions(
        proportions=[prop("ENST1", 0.2), prop("ENST2", 0.2)],
        eligible_transcripts=[tx("ENST1"), tx("ENST2")],
        snapshot=snapshot,
        policy="renormalize_with_warning",
    )
    assert not valid
    assert "renormalization_requires_explicit_materiality_review" in errors


def test_missing_transcript_handling_and_annotation_release_mismatch(snapshot, policy) -> None:
    gene, weights, _ = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1"), tx("ENST2")],
        policy=policy,
        external_proportions=[prop("ENST1", 1.0, release="wrong")],
    )
    assert gene.isoform_resolution_status == "invalid_external_proportions"
    assert weights == []
    assert "annotation_release_mismatch" in gene.warnings


def test_source_method_provenance(snapshot, policy) -> None:
    _gene, weights, _ = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1")],
        policy=policy,
        external_proportions=[prop("ENST1", 1.0)],
    )
    assert weights[0].source_method == "precomputed_transcript_proportions"
    assert weights[0].provenance_record_ids == ("sha256:props",)
