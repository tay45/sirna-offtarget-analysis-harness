from __future__ import annotations

import math

import pytest

from sirna_offtarget.isoform_uncertainty.contracts import (
    ExternalTranscriptProportionPolicyV1,
    ExternalTranscriptProportionRecordV1,
    GeneIsoformUncertaintyRecordV1,
    IsoformUncertaintyRunRecordV1,
    TranscriptPriorWeightRecordV1,
    TranscriptSetPolicyV1,
)
from sirna_offtarget.isoform_uncertainty.core import (
    IsoformUncertaintyPolicyError,
    assign_isoform_uncertainty_for_gene,
    validate_annotation_snapshot,
)
from tests.unit.isoform_uncertainty.conftest import tx
from tests.unit.isoform_uncertainty.external_proportions.test_external_proportions import prop


def test_annotation_validation_reports_conflicts_and_duplicates(snapshot) -> None:
    validation = validate_annotation_snapshot(
        snapshot,
        [
            tx("ENST1", organism="mouse"),
            tx("ENST1", assembly="GRCm39"),
            tx("ENST2").model_copy(update={"canonical_transcript_id": None}),
        ],
    )

    assert validation.duplicates == 1
    assert validation.organism_conflicts == 1
    assert validation.assembly_conflicts == 1
    assert validation.unresolved_transcripts == 1
    assert "duplicate transcript identifiers present" in validation.fatal_errors
    assert "annotation organism conflicts with snapshot" in validation.fatal_errors
    assert "annotation assembly conflicts with snapshot" in validation.fatal_errors


def test_transcript_policy_exclusion_branches(snapshot) -> None:
    policy = TranscriptSetPolicyV1(
        include_protein_coding=False,
        include_retained_intron=False,
        include_nonsense_mediated_decay=False,
        include_processed_transcript=False,
        include_noncoding=False,
        include_pseudogene=False,
        include_readthrough=False,
        allowed_transcript_support_levels=("1",),
    )

    _gene, _weights, exclusions = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[
            tx("ENST1", biotype="protein_coding"),
            tx("ENST2", biotype="retained_intron"),
            tx("ENST3", biotype="nonsense_mediated_decay"),
            tx("ENST4", biotype="processed_transcript"),
            tx("ENST5", biotype="processed_pseudogene"),
            tx("ENST6", biotype="readthrough_transcript"),
            tx("ENST7", biotype="lncRNA"),
        ],
        policy=policy,
    )

    assert {item.exclusion_reason for item in exclusions} == {
        "protein_coding_excluded",
        "retained_intron_excluded",
        "nonsense_mediated_decay_excluded",
        "processed_transcript_excluded",
        "pseudogene_transcript_excluded",
        "readthrough_transcript_excluded",
        "noncoding_transcript_excluded",
    }
    support_policy = TranscriptSetPolicyV1(allowed_transcript_support_levels=("1",))
    _gene, _weights, support_exclusions = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST8").model_copy(update={"transcript_support_level": "5"})],
        policy=support_policy,
    )
    assert support_exclusions[0].exclusion_reason == "transcript_support_level_excluded"


def test_external_proportion_missing_transcript_is_invalid_by_default(snapshot, policy) -> None:
    gene, weights, _exclusions = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1"), tx("ENST2")],
        policy=policy,
        external_proportions=[prop("ENST1", 1.0)],
    )

    assert gene.weight_sum == 0.0
    assert gene.isoform_resolution_status == "invalid_external_proportions"
    assert "missing_transcript_proportion" in gene.warnings
    assert weights == []


def test_external_proportion_missing_transcript_can_be_zero_by_policy(snapshot, policy) -> None:
    gene, weights, _exclusions = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1"), tx("ENST2")],
        policy=policy,
        external_proportions=[prop("ENST1", 1.0)],
        external_policy=ExternalTranscriptProportionPolicyV1(
            missing_transcript_behavior="missing_as_zero"
        ),
    )

    assert gene.weight_sum == 1.0
    assert [item.weight for item in weights] == [1.0, 0.0]
    assert weights[1].weight_evidence_status == (
        "external_proportion_missing_treated_as_zero_by_policy"
    )


def test_external_proportion_sum_failure_is_not_silently_repaired(snapshot, policy) -> None:
    gene, weights, _exclusions = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1"), tx("ENST2")],
        policy=policy,
        external_proportions=[prop("ENST1", 0.5)],
        tolerance=1e-12,
    )
    assert gene.isoform_resolution_status == "invalid_external_proportions"
    assert "proportion_sum_outside_tolerance" in gene.warnings
    assert weights == []


def test_external_missing_transcript_can_fallback_to_equal_prior(snapshot, policy) -> None:
    gene, weights, _exclusions = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1"), tx("ENST2")],
        policy=policy,
        external_proportions=[prop("ENST1", 1.0)],
        external_policy=ExternalTranscriptProportionPolicyV1(
            missing_transcript_behavior="fallback_to_equal_prior"
        ),
    )

    assert gene.prior_method == "equal_weight_per_eligible_transcript_after_missing_external"
    assert [item.weight for item in weights] == [0.5, 0.5]


def test_external_policy_fail_stage_raises(snapshot, policy) -> None:
    with pytest.raises(IsoformUncertaintyPolicyError):
        assign_isoform_uncertainty_for_gene(
            source_expression_v2_record_id="expr-r1",
            original_gene_id="TP53",
            canonical_gene_id="HGNC:11998",
            approved_symbol="TP53",
            organism="human",
            assembly="GRCh38",
            annotation_snapshot=snapshot,
            annotation_records=[tx("ENST1"), tx("ENST2")],
            policy=policy,
            external_proportions=[prop("ENST1", 0.5)],
            external_policy=ExternalTranscriptProportionPolicyV1(
                invalid_proportion_behavior="fail_stage"
            ),
        )


def test_contract_validators_reject_weight_and_gene_count_overclaims() -> None:
    base_weight = {
        "record_id": "w",
        "gene_isoform_uncertainty_record_id": "g",
        "original_gene_id": "TP53",
        "canonical_gene_id": "HGNC:11998",
        "original_transcript_id": "ENST1.1",
        "canonical_transcript_id": "ENST1",
        "transcript_version": "1",
        "transcript_biotype": "protein_coding",
        "annotation_status": "annotation_eligible",
        "eligibility_status": "eligible",
        "exclusion_reason": None,
        "weight_type": "equal_prior",
        "weight_source": "annotation_only_equal_prior",
        "weight_evidence_status": "assumption_due_to_unresolved_isoform_abundance",
    }
    assert TranscriptPriorWeightRecordV1.model_validate(base_weight | {"weight": None})
    with pytest.raises(ValueError):
        TranscriptPriorWeightRecordV1.model_validate(base_weight | {"weight": math.inf})

    base_gene = {
        "record_id": "g",
        "source_expression_v2_record_id": "expr",
        "original_gene_id": "TP53",
        "canonical_gene_id": "HGNC:11998",
        "approved_symbol": "TP53",
        "organism": "human",
        "assembly": "GRCh38",
        "annotation_snapshot_id": "ann",
        "annotation_checksum": "sha256:ann",
        "transcript_set_policy_id": "policy",
        "annotated_transcript_count": 0,
        "eligible_transcript_count": 0,
        "excluded_transcript_count": 0,
        "isoform_evidence_mode": "annotation_only_equal_prior",
        "isoform_resolution_status": "no_eligible_transcripts",
        "prior_method": "none",
        "weight_sum": 0.0,
        "transcript_weight_record_ids": (),
    }
    with pytest.raises(ValueError, match="no weights"):
        GeneIsoformUncertaintyRecordV1.model_validate(
            base_gene | {"transcript_weight_record_ids": ("w",)}
        )
    with pytest.raises(ValueError, match="positive weight"):
        GeneIsoformUncertaintyRecordV1.model_validate(base_gene | {"weight_sum": 1.0})


def test_external_proportion_and_run_validators_cover_failure_edges() -> None:
    with pytest.raises(ValueError):
        ExternalTranscriptProportionRecordV1.model_validate(
            prop("ENST1", 0.1).model_dump() | {"proportion": math.inf}
        )
    with pytest.raises(ValueError):
        ExternalTranscriptProportionRecordV1.model_validate(
            prop("ENST1", 0.1).model_dump() | {"proportion": 1.1}
        )

    base_run = {
        "run_id": "run",
        "expression_stage_contract": "ExpressionAnalysisResultV2",
        "expression_artifact_checksum": "sha256:expr",
        "annotation_snapshot_id": "ann",
        "annotation_checksum": "sha256:ann",
        "transcript_set_policy_id": "policy",
        "isoform_evidence_mode": "annotation_only_equal_prior",
        "weight_policy": "equal_prior",
        "numerical_tolerance": 1e-6,
        "organism": "human",
        "assembly": "GRCh38",
        "identifier_snapshot_id": "ids",
        "identifier_snapshot_checksum": "sha256:ids",
        "software_version": "0.1.0",
        "started_at": "2026-06-26T00:00:00Z",
        "completed_at": "2026-06-26T00:00:01Z",
        "status": "completed",
        "record_counts": {},
        "output_checksums": {"run": "sha256:run"},
    }
    assert IsoformUncertaintyRunRecordV1.model_validate(base_run)
    with pytest.raises(ValueError, match="timestamps"):
        IsoformUncertaintyRunRecordV1.model_validate(base_run | {"started_at": ""})
    with pytest.raises(ValueError, match="annotation checksum"):
        IsoformUncertaintyRunRecordV1.model_validate(base_run | {"annotation_checksum": ""})
    assert IsoformUncertaintyRunRecordV1.model_validate(
        base_run | {"status": "failed", "output_checksums": {}, "annotation_checksum": ""}
    )
