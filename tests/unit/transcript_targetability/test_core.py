from __future__ import annotations

import json

import pytest

from sirna_offtarget.transcript_targetability.contracts import (
    CleavageCompatibilityPolicyV1,
    IntendedTargetValidationPolicyV1,
    MissingTranscriptSequencePolicyV1,
    SeedMatchPolicyV1,
    TranscriptSequenceRecordV1,
    TranscriptSequenceSnapshotV1,
)
from sirna_offtarget.transcript_targetability.core import (
    find_transcript_targetability,
    load_transcript_sequence_snapshot,
    normalize_sirna_sequence,
    reverse_complement,
    sha256_text,
    unavailable_sequence_evidence,
    validate_intended_target_actual_site,
    validate_sirna_sequence,
    validate_transcript_sequence_snapshot,
)


def _sirna():
    sirna, validation = validate_sirna_sequence(
        sirna_id="sirna1",
        reagent_name="reagent1",
        guide_sequence="AAAAAAAAAAAAAAAAAAAAA",
        organism="human",
        assembly="GRCh38",
        intended_target_gene_id="GENE1",
        intended_target_transcript_ids=("TX1",),
    )
    return sirna, validation


def _transcript(transcript_id: str = "TX1", sequence: str = "GGGTTTTTTTTTTTTTTTTTTTTTCCC"):
    return TranscriptSequenceRecordV1(
        canonical_gene_id="GENE1",
        canonical_transcript_id=transcript_id,
        transcript_version="1",
        sequence=sequence,
        sequence_checksum=sha256_text(sequence),
    )


def test_sirna_sequence_validation_requires_clean_explicit_guide() -> None:
    normalized, alphabet = normalize_sirna_sequence("aa uu")
    assert normalized == "AATT"
    assert alphabet == "RNA"
    assert reverse_complement("AATT") == "AATT"
    with pytest.raises(ValueError, match="mixed RNA/DNA"):
        normalize_sirna_sequence("AUTT")
    with pytest.raises(ValueError, match="must not be empty"):
        normalize_sirna_sequence("   ")
    with pytest.raises(ValueError, match="unsupported bases"):
        normalize_sirna_sequence("AA-BB")
    with pytest.raises(ValueError, match="orientation"):
        validate_sirna_sequence(
            sirna_id="bad",
            reagent_name="bad",
            guide_sequence="AAAA",
            organism="human",
            assembly="GRCh38",
            guide_orientation="unknown",
        )


def test_passenger_sequence_is_validated_when_supplied() -> None:
    sirna, validation = validate_sirna_sequence(
        sirna_id="sirna2",
        reagent_name="reagent2",
        guide_sequence="AAAAAAAAAAAAAAAAAAAAA",
        passenger_sequence="UUUUUUUUUUUUUUUUUUUUU",
        organism="human",
        assembly="GRCh38",
    )
    assert sirna.passenger_sequence_status == "explicit"
    assert sirna.passenger_sequence_normalized == "TTTTTTTTTTTTTTTTTTTTT"
    assert validation.passenger_valid is True


def test_guide_length_policy_is_enforced_and_recorded() -> None:
    policy = CleavageCompatibilityPolicyV1(guide_length_min=20, guide_length_max=21)
    with pytest.raises(ValueError, match="below configured minimum"):
        validate_sirna_sequence(
            sirna_id="short",
            reagent_name="short",
            guide_sequence="A" * 19,
            organism="human",
            assembly="GRCh38",
            cleavage_policy=policy,
        )
    sirna, validation = validate_sirna_sequence(
        sirna_id="ok",
        reagent_name="ok",
        guide_sequence="A" * 20,
        organism="human",
        assembly="GRCh38",
        cleavage_policy=policy,
        passenger_search_requested=True,
    )
    assert sirna.guide_length == 20
    assert validation.guide_length_min == 20
    assert validation.guide_length_max == 21
    assert validation.passenger_search_status == "unsupported"


def test_seed_policy_rejects_unsupported_runtime_options() -> None:
    with pytest.raises(ValueError, match="exact_seed_required conflicts"):
        SeedMatchPolicyV1(exact_seed_required=True, allowed_seed_mismatches=1)
    with pytest.raises(ValueError, match="minimum_total_paired_bases"):
        SeedMatchPolicyV1(minimum_total_paired_bases=6)
    with pytest.raises(ValueError, match="unsupported_supplementary_pairing_policy"):
        SeedMatchPolicyV1(supplementary_pairing_requirement="required")
    with pytest.raises(ValueError, match="unsupported_transcript_region_restrictions"):
        SeedMatchPolicyV1(transcript_region_restrictions=("3utr",))


def test_exact_targetability_site_records_all_aligned_base_statuses() -> None:
    sirna, _validation = _sirna()
    evidence, sites, mismatches, positions = find_transcript_targetability(
        sirna=sirna,
        transcript=_transcript(),
        transcript_prior_weight=1.0,
        source_isoform_uncertainty_record_id="gene-iu",
        source_transcript_weight_record_id="weight-1",
        transcript_sequence_snapshot_id="seq-snapshot",
    )
    assert evidence.targetability_decision_status == "cleavage_candidate_present"
    assert sites[0].evidence_class == "exact_full_length_complement"
    assert sites[0].cleavage_compatibility_status == "cleavage_compatible_candidate"
    first_site_bases = [
        record for record in positions if record.site_record_id == sites[0].site_record_id
    ]
    assert len(first_site_bases) == sirna.guide_length
    assert {record.pairing_status for record in first_site_bases} == {"match"}


def test_seed_only_evidence_is_kept_separate_from_cleavage_compatible() -> None:
    sirna, _validation = _sirna()
    site_sequence = "ATTTTTTTTAAAAAAAAAAAA"
    evidence, sites, mismatches, positions = find_transcript_targetability(
        sirna=sirna,
        transcript=_transcript(sequence=site_sequence),
        transcript_prior_weight=1.0,
        source_isoform_uncertainty_record_id="gene-iu",
        source_transcript_weight_record_id="weight-1",
        transcript_sequence_snapshot_id="seq-snapshot",
    )
    assert evidence.targetability_decision_status == "seed_only_candidate_present"
    assert sites[0].evidence_class == "seed_only_candidate"
    assert sites[0].cleavage_compatibility_status == "not_cleavage_compatible"
    assert any(record.match_status == "mismatch" for record in mismatches)
    assert sites[0].seed_mismatch_count == 0


def test_seed_only_candidate_requires_minimum_total_paired_bases() -> None:
    sirna, _validation = _sirna()
    site_sequence = "ATTTTTTTTAAAAAAAAAAAA"
    evidence, sites, _mismatches, _positions = find_transcript_targetability(
        sirna=sirna,
        transcript=_transcript(sequence=site_sequence),
        transcript_prior_weight=1.0,
        source_isoform_uncertainty_record_id="gene-iu",
        source_transcript_weight_record_id="weight-1",
        transcript_sequence_snapshot_id="seq-snapshot",
        seed_policy=SeedMatchPolicyV1(minimum_total_paired_bases=21),
    )
    assert evidence.targetability_decision_status == "indeterminate"
    assert sites[0].evidence_class == "partial_nonseed_match"
    assert sites[0].paired_base_policy_status == "failed"


def test_short_transcript_records_no_supported_site() -> None:
    sirna, _validation = _sirna()
    evidence, sites, mismatches, positions = find_transcript_targetability(
        sirna=sirna,
        transcript=_transcript(sequence="TTTT"),
        transcript_prior_weight=None,
        source_isoform_uncertainty_record_id="gene-iu",
        source_transcript_weight_record_id="weight-1",
        transcript_sequence_snapshot_id="seq-snapshot",
    )
    assert evidence.targetability_decision_status == "no_supported_site"
    assert sites == []
    assert mismatches == []
    assert positions == []


def test_transcript_sequence_snapshot_rejects_missing_and_wrong_gene_records() -> None:
    snapshot = TranscriptSequenceSnapshotV1(
        snapshot_id="seq-snapshot",
        provider="local",
        release="annotation-snapshot",
        organism="human",
        assembly="GRCh38",
        transcript_identifier_namespace="canonical_transcript_id",
        transcript_count=1,
        sequence_file_checksum="abc",
        verification_status="verified",
        generation_method="unit_test",
    )
    validation = validate_transcript_sequence_snapshot(
        snapshot=snapshot,
        records=[_transcript(transcript_id="TX1")],
        expected_organism="human",
        expected_assembly="GRCh38",
        expected_release="annotation-snapshot",
        eligible_transcripts={"TX1": "OTHER", "TX2": "GENE1"},
    )
    assert validation.verification_status == "failed"
    assert "TX2" in validation.missing_eligible_transcripts
    assert "TX1" in validation.wrong_gene_assignments


def test_missing_transcript_sequence_policy_can_preserve_unavailable_evidence() -> None:
    policy = MissingTranscriptSequencePolicyV1(mode="record_unavailable_and_continue")
    assert policy.mode == "record_unavailable_and_continue"
    sirna, _validation = _sirna()
    validation = validate_transcript_sequence_snapshot(
        snapshot=TranscriptSequenceSnapshotV1(
            snapshot_id="seq-snapshot",
            provider="local",
            release="annotation-snapshot",
            organism="human",
            assembly="GRCh38",
            transcript_identifier_namespace="canonical_transcript_id",
            transcript_count=0,
            sequence_file_checksum="abc",
            verification_status="verified",
            generation_method="unit_test",
        ),
        records=[],
        expected_organism="human",
        expected_assembly="GRCh38",
        expected_release="annotation-snapshot",
        eligible_transcripts={"TX1": "GENE1"},
        require_complete_sequences=False,
    )
    evidence = unavailable_sequence_evidence(
        sirna=sirna,
        canonical_gene_id="GENE1",
        canonical_transcript_id="TX1",
        transcript_version=None,
        transcript_prior_weight=1.0,
        source_isoform_uncertainty_record_id="gene-iu",
        source_transcript_weight_record_id="weight-1",
    )
    assert validation.verification_status == "verified"
    assert validation.missing_eligible_transcripts == ("TX1",)
    assert evidence.sequence_available is False
    assert evidence.targetability_decision_status == "sequence_unavailable"


def test_intended_target_actual_site_validation_requires_acceptable_site() -> None:
    sirna, _validation = _sirna()
    evidence, sites, _mismatches, _positions = find_transcript_targetability(
        sirna=sirna,
        transcript=_transcript(),
        transcript_prior_weight=1.0,
        source_isoform_uncertainty_record_id="gene-iu",
        source_transcript_weight_record_id="weight-1",
        transcript_sequence_snapshot_id="seq-snapshot",
    )
    record = validate_intended_target_actual_site(
        intended_transcript_ids=("TX1",),
        evidence_records=[evidence],
        site_records=sites,
        policy=IntendedTargetValidationPolicyV1(),
    )
    assert record.validation_status == "passed"
    assert record.errors == ()

    failed = validate_intended_target_actual_site(
        intended_transcript_ids=("TX2",),
        evidence_records=[evidence],
        site_records=sites,
    )
    assert failed.validation_status == "failed"
    assert failed.errors == ("intended_target_transcript_missing:TX2",)


def test_intended_target_gene_only_validation_preserves_uncertainty() -> None:
    record = validate_intended_target_actual_site(
        intended_target_gene_id="GENE1",
        intended_transcript_ids=(),
        evidence_records=[],
        site_records=[],
    )
    assert record.validation_status == "uncertain"
    assert record.supplied_input_status == "gene_only"


def test_transcript_sequence_snapshot_rejects_status_release_and_checksum_errors() -> None:
    sequence = "ACACACACAC"
    snapshot = TranscriptSequenceSnapshotV1(
        snapshot_id="seq-snapshot",
        provider="local",
        release="other-release",
        organism="mouse",
        assembly="GRCm39",
        transcript_identifier_namespace="canonical_transcript_id",
        transcript_count=1,
        sequence_file_checksum="abc",
        verification_status="unverified",
        generation_method="unit_test",
    )
    validation = validate_transcript_sequence_snapshot(
        snapshot=snapshot,
        records=[
            TranscriptSequenceRecordV1(
                canonical_gene_id="GENE1",
                canonical_transcript_id="TX1",
                transcript_version="1",
                sequence=sequence,
                sequence_checksum="wrong",
            )
        ],
        expected_organism="human",
        expected_assembly="GRCh38",
        expected_release="annotation-snapshot",
        eligible_transcripts={"TX1": "GENE1"},
    )
    assert validation.verification_status == "failed"
    assert "sequence snapshot is not verified" in validation.fatal_errors
    assert "annotation and sequence release mismatch" in validation.fatal_errors
    assert "organism mismatch" in validation.fatal_errors
    assert "assembly mismatch" in validation.fatal_errors
    assert "TX1" in validation.invalid_sequence_ids


def test_transcript_sequence_snapshot_loader_validates_file_checksum(tmp_path) -> None:
    snapshot = tmp_path / "cache" / "snap1"
    snapshot.mkdir(parents=True)
    records = snapshot / "transcript_sequences.jsonl"
    records.write_text(
        json.dumps(
            {
                "canonical_gene_id": "GENE1",
                "canonical_transcript_id": "TX1",
                "sequence": "ACGT",
            }
        )
        + "\n"
    )
    (snapshot / "manifest.json").write_text(
        json.dumps(
            {
                "snapshot_id": "snap1",
                "provider": "local",
                "release": "rel1",
                "organism": "human",
                "assembly": "GRCh38",
                "transcript_identifier_namespace": "canonical_transcript_id",
                "transcript_count": 1,
                "sequence_file_checksum": "wrong",
                "verification_status": "verified",
                "generation_method": "unit_test",
            }
        )
    )
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        load_transcript_sequence_snapshot(tmp_path / "cache", "snap1")


def test_transcript_sequence_snapshot_loader_reports_missing_files(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="missing transcript sequence manifest"):
        load_transcript_sequence_snapshot(tmp_path / "cache", "missing")
    snapshot = tmp_path / "cache" / "snap1"
    snapshot.mkdir(parents=True)
    (snapshot / "manifest.json").write_text(
        json.dumps(
            {
                "snapshot_id": "snap1",
                "provider": "local",
                "release": "rel1",
                "organism": "human",
                "assembly": "GRCh38",
                "transcript_identifier_namespace": "canonical_transcript_id",
                "transcript_count": 1,
                "sequence_file_checksum": "",
                "verification_status": "verified",
                "generation_method": "unit_test",
            }
        )
    )
    with pytest.raises(RuntimeError, match="missing transcript sequence records"):
        load_transcript_sequence_snapshot(tmp_path / "cache", "snap1")


def test_transcript_sequence_snapshot_detects_duplicate_records() -> None:
    snapshot = TranscriptSequenceSnapshotV1(
        snapshot_id="seq-snapshot",
        provider="local",
        release="annotation-snapshot",
        organism="human",
        assembly="GRCh38",
        transcript_identifier_namespace="canonical_transcript_id",
        transcript_count=2,
        sequence_file_checksum="abc",
        verification_status="verified",
        generation_method="unit_test",
    )
    validation = validate_transcript_sequence_snapshot(
        snapshot=snapshot,
        records=[_transcript("TX1"), _transcript("TX1")],
        expected_organism="human",
        expected_assembly="GRCh38",
        expected_release=None,
        eligible_transcripts={"TX1": "GENE1"},
    )
    assert "TX1" in validation.duplicate_sequence_ids
    assert any(error.startswith("duplicate sequence id:") for error in validation.fatal_errors)


def test_transcript_sequence_record_rejects_empty_and_unsupported_sequences() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        TranscriptSequenceRecordV1(
            canonical_gene_id="GENE1",
            canonical_transcript_id="TX1",
            sequence="",
        )
    with pytest.raises(ValueError, match="unsupported bases"):
        TranscriptSequenceRecordV1(
            canonical_gene_id="GENE1",
            canonical_transcript_id="TX1",
            sequence="ACGN",
        )


def test_targetability_policies_reject_gapped_or_invalid_coordinates() -> None:
    with pytest.raises(ValueError, match="ungapped"):
        CleavageCompatibilityPolicyV1(allowed_indels=True)
    with pytest.raises(ValueError, match="non-negative"):
        CleavageCompatibilityPolicyV1(maximum_total_mismatches=-1)
    with pytest.raises(ValueError, match="invalid seed"):
        CleavageCompatibilityPolicyV1(seed_start=8, seed_end=2)
    with pytest.raises(ValueError, match="invalid central"):
        CleavageCompatibilityPolicyV1(central_region_start=12, central_region_end=9)
    with pytest.raises(ValueError, match="invalid seed"):
        SeedMatchPolicyV1(seed_start=8, seed_end=2)
    with pytest.raises(ValueError, match="seed_length"):
        SeedMatchPolicyV1(seed_length=8)
    with pytest.raises(ValueError, match="non-negative"):
        SeedMatchPolicyV1(allowed_seed_mismatches=-1)
    with pytest.raises(ValueError, match="ungapped"):
        SeedMatchPolicyV1(allowed_bulges=True)
    assert CleavageCompatibilityPolicyV1().fingerprint.startswith("cleavage-policy-")
    assert SeedMatchPolicyV1().fingerprint.startswith("seed-policy-")


def test_contract_records_are_json_serializable() -> None:
    sirna, validation = _sirna()
    payload = sirna.model_dump(mode="json") | validation.model_dump(mode="json")
    assert json.loads(json.dumps(payload))
