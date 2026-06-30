from __future__ import annotations

from sirna_offtarget.transcript_targetability.contracts import IntendedTargetValidationPolicyV1
from sirna_offtarget.transcript_targetability.core import (
    find_transcript_targetability,
    validate_intended_target_actual_site,
)
from tests.unit.transcript_targetability.test_core import _sirna, _transcript


def _evidence_and_sites(sequence: str = "GGGTTTTTTTTTTTTTTTTTTTTTCCC"):
    sirna, _validation = _sirna()
    evidence, sites, _mismatches, _positions = find_transcript_targetability(
        sirna=sirna,
        transcript=_transcript(sequence=sequence),
        transcript_prior_weight=1.0,
        source_isoform_uncertainty_record_id="gene-iu",
        source_transcript_weight_record_id="weight-1",
        transcript_sequence_snapshot_id="seq-snapshot",
    )
    return [evidence], sites


def test_intended_target_required_missing_input_fails() -> None:
    record = validate_intended_target_actual_site(
        intended_transcript_ids=(),
        evidence_records=[],
        site_records=[],
        policy=IntendedTargetValidationPolicyV1(intended_target_required=True),
    )

    assert record.validation_status == "failed"
    assert "intended_target_input_missing" in record.errors


def test_intended_target_not_required_records_not_requested() -> None:
    record = validate_intended_target_actual_site(
        intended_transcript_ids=(),
        evidence_records=[],
        site_records=[],
        policy=IntendedTargetValidationPolicyV1(intended_target_required=False),
    )

    assert record.validation_status == "not_requested"
    assert record.supplied_input_status == "not_requested"


def test_transcript_ids_required_rejects_gene_only_input() -> None:
    record = validate_intended_target_actual_site(
        intended_target_gene_id="GENE1",
        intended_transcript_ids=(),
        evidence_records=[],
        site_records=[],
        policy=IntendedTargetValidationPolicyV1(transcript_ids_required=True),
    )

    assert record.validation_status == "failed"
    assert "intended_target_transcript_ids_required" in record.errors


def test_gene_only_warning_and_preserve_uncertain_behavior() -> None:
    warning = validate_intended_target_actual_site(
        intended_target_gene_id="GENE1",
        intended_transcript_ids=(),
        evidence_records=[],
        site_records=[],
        policy=IntendedTargetValidationPolicyV1(gene_only_behavior="warning"),
    )
    uncertain = validate_intended_target_actual_site(
        intended_target_gene_id="GENE1",
        intended_transcript_ids=(),
        evidence_records=[],
        site_records=[],
        policy=IntendedTargetValidationPolicyV1(gene_only_behavior="preserve_uncertainty"),
    )

    assert warning.validation_status == "warning"
    assert uncertain.validation_status == "uncertain"


def test_gene_only_fail_stage_behavior() -> None:
    record = validate_intended_target_actual_site(
        intended_target_gene_id="GENE1",
        intended_transcript_ids=(),
        evidence_records=[],
        site_records=[],
        policy=IntendedTargetValidationPolicyV1(gene_only_behavior="fail_stage"),
    )

    assert record.validation_status == "failed"
    assert "gene_only_intended_target_not_allowed" in record.errors


def test_gene_only_accept_any_gene_transcript_site_behavior() -> None:
    evidence, sites = _evidence_and_sites()
    record = validate_intended_target_actual_site(
        intended_target_gene_id="GENE1",
        intended_transcript_ids=(),
        evidence_records=evidence,
        site_records=sites,
        policy=IntendedTargetValidationPolicyV1(
            gene_only_behavior="accept_any_gene_transcript_site"
        ),
    )

    assert record.validation_status == "passed"
    assert record.best_accepted_site_id == sites[0].site_record_id


def test_failure_behavior_warning_and_preserve_invalid() -> None:
    warning = validate_intended_target_actual_site(
        intended_transcript_ids=("MISSING",),
        evidence_records=[],
        site_records=[],
        policy=IntendedTargetValidationPolicyV1(failure_behavior="warning"),
    )
    preserved = validate_intended_target_actual_site(
        intended_transcript_ids=("MISSING",),
        evidence_records=[],
        site_records=[],
        policy=IntendedTargetValidationPolicyV1(failure_behavior="preserve_invalid_with_status"),
    )

    assert warning.validation_status == "warning"
    assert preserved.validation_status == "invalid_preserved"


def test_accepted_evidence_classes_and_thresholds_are_enforced() -> None:
    evidence, sites = _evidence_and_sites("ATTTTTTTTAAAAAAAAAAAA")
    record = validate_intended_target_actual_site(
        intended_transcript_ids=("TX1",),
        evidence_records=evidence,
        site_records=sites,
        policy=IntendedTargetValidationPolicyV1(
            accepted_evidence_classes=("exact_full_length_complement",),
            maximum_total_mismatches=0,
            maximum_seed_mismatches=0,
            maximum_central_mismatches=0,
        ),
    )

    assert record.validation_status == "failed"
    assert record.rejected_site_ids
    assert "evidence_class_not_accepted" in record.rejection_reasons[sites[0].site_record_id]


def test_best_acceptable_intended_site_recorded() -> None:
    evidence, sites = _evidence_and_sites()
    record = validate_intended_target_actual_site(
        intended_transcript_ids=("TX1",),
        evidence_records=evidence,
        site_records=sites,
    )

    assert record.validation_status == "passed"
    assert record.accepted_site_ids
    assert record.best_accepted_site_id == sites[0].site_record_id
