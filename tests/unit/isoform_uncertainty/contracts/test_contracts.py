from __future__ import annotations

import pytest

from sirna_offtarget.isoform_uncertainty.contracts import (
    GeneIsoformUncertaintyRecordV1,
    IsoformUncertaintyRunRecordV1,
    TranscriptAnnotationValidationRecordV1,
    TranscriptPriorWeightRecordV1,
    TranscriptSetExclusionRecordV1,
    stable_id,
)


def test_gene_isoform_uncertainty_record_v1() -> None:
    record = GeneIsoformUncertaintyRecordV1(
        record_id="g1",
        source_expression_v2_record_id="expr1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot_id="ann1",
        annotation_checksum="sha256:ann",
        transcript_set_policy_id="policy",
        annotated_transcript_count=2,
        eligible_transcript_count=2,
        excluded_transcript_count=0,
        isoform_evidence_mode="annotation_only_equal_prior",
        isoform_resolution_status="multiple_transcripts_equal_prior",
        prior_method="equal_weight_per_eligible_transcript",
        weight_sum=1.0,
        transcript_weight_record_ids=("w1", "w2"),
    )
    assert record.schema_version == "1"


def test_transcript_prior_weight_record_v1_validation() -> None:
    record = TranscriptPriorWeightRecordV1(
        record_id="w1",
        gene_isoform_uncertainty_record_id="g1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        original_transcript_id="ENST1.1",
        canonical_transcript_id="ENST1",
        transcript_version="1",
        transcript_biotype="protein_coding",
        annotation_status="annotation_eligible",
        eligibility_status="eligible",
        exclusion_reason=None,
        weight=1.0,
        weight_type="equal_prior",
        weight_source="annotation_only_equal_prior",
        weight_evidence_status="assumption_due_to_unresolved_isoform_abundance",
    )
    assert record.weight == 1.0
    with pytest.raises(ValueError):
        TranscriptPriorWeightRecordV1.model_validate(record.model_dump() | {"weight": 2.0})
    with pytest.raises(ValueError):
        TranscriptPriorWeightRecordV1.model_validate(
            record.model_dump() | {"weight_source": "measured_isoform_fraction"}
        )


def test_transcript_set_exclusion_and_annotation_validation_records() -> None:
    exclusion = TranscriptSetExclusionRecordV1(
        record_id="e1",
        canonical_gene_id="HGNC:11998",
        transcript_id="ENST1",
        policy_id="policy",
        exclusion_reason="missing_sequence_reference",
        annotation_snapshot_id="ann1",
    )
    validation = TranscriptAnnotationValidationRecordV1(
        annotation_snapshot_id="ann1",
        total_rows=1,
        unique_genes=1,
        unique_transcripts=1,
        duplicates=0,
        invalid_mappings=0,
        unresolved_genes=0,
        unresolved_transcripts=0,
        assembly_conflicts=0,
        organism_conflicts=0,
        missing_sequence_references=1,
    )
    assert exclusion.exclusion_reason == "missing_sequence_reference"
    assert validation.missing_sequence_references == 1


def test_isoform_uncertainty_run_record_v1_requires_completed_outputs() -> None:
    with pytest.raises(ValueError):
        IsoformUncertaintyRunRecordV1(
            run_id="run",
            expression_stage_contract="ExpressionAnalysisResultV2",
            expression_artifact_checksum="sha256:expr",
            annotation_snapshot_id="ann",
            annotation_checksum="sha256:ann",
            transcript_set_policy_id="policy",
            isoform_evidence_mode="annotation_only_equal_prior",
            weight_policy="equal_prior",
            numerical_tolerance=1e-6,
            organism="human",
            assembly="GRCh38",
            identifier_snapshot_id="ids",
            identifier_snapshot_checksum="sha256:ids",
            software_version="0.1.0",
            started_at="2026-06-26T00:00:00Z",
            completed_at="2026-06-26T00:00:01Z",
            status="completed",
            record_counts={},
            output_checksums={},
        )


def test_deterministic_record_ids() -> None:
    assert stable_id("x", "a", {"b": 1}) == stable_id("x", "a", {"b": 1})
    assert stable_id("x", "a", {"b": 1}) != stable_id("x", "a", {"b": 2})
