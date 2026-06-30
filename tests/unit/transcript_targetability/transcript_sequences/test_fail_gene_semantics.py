from __future__ import annotations

from sirna_offtarget.transcript_targetability.contracts import MissingTranscriptSequencePolicyV1
from sirna_offtarget.transcript_targetability.core import (
    build_gene_failure_record,
    gene_failed_evidence,
)
from tests.unit.transcript_targetability.test_core import _sirna


def test_fail_gene_marks_entire_gene_failed() -> None:
    policy = MissingTranscriptSequencePolicyV1(mode="fail_gene")
    record = build_gene_failure_record(
        canonical_gene_id="GENE1",
        affected_transcript_ids=("TX1", "TX2"),
        triggering_transcript_ids=("TX2",),
        missing_sequence_policy_id=policy.policy_id,
        source_isoform_uncertainty_record_ids=("gene-iu",),
    )

    assert record.canonical_gene_id == "GENE1"
    assert record.affected_transcript_ids == ("TX1", "TX2")
    assert record.triggering_transcript_ids == ("TX2",)
    assert record.failure_reason == "gene_failed_missing_transcript_sequence"


def test_fail_gene_marks_all_gene_transcripts_not_evaluated() -> None:
    sirna, _validation = _sirna()
    evidence = gene_failed_evidence(
        sirna=sirna,
        canonical_gene_id="GENE1",
        canonical_transcript_id="TX1",
        transcript_version="1",
        transcript_prior_weight=0.5,
        source_isoform_uncertainty_record_id="gene-iu",
        source_transcript_weight_record_id="weight-1",
        triggering_transcript_ids=("TX2",),
    )

    assert evidence.sequence_available is False
    assert evidence.site_record_ids == ()
    assert evidence.targetability_decision_status == "not_evaluated_due_to_gene_failure"


def test_fail_gene_does_not_equal_continue_mode() -> None:
    fail_gene = MissingTranscriptSequencePolicyV1(mode="fail_gene")
    continue_mode = MissingTranscriptSequencePolicyV1(mode="record_unavailable_and_continue")

    assert fail_gene.mode != continue_mode.mode


def test_fail_gene_does_not_equal_fail_stage() -> None:
    fail_gene = MissingTranscriptSequencePolicyV1(mode="fail_gene")
    fail_stage = MissingTranscriptSequencePolicyV1(mode="fail_stage")

    assert fail_gene.mode != fail_stage.mode
