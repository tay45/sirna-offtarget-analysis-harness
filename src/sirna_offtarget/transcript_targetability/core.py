from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from sirna_offtarget.transcript_targetability.contracts import (
    CleavageCompatibilityPolicyV1,
    IntendedTargetValidationPolicyV1,
    IntendedTargetValidationRecordV1,
    SeedMatchPolicyV1,
    SiRNASequenceRecordV1,
    SiRNASequenceValidationRecordV1,
    TranscriptSequenceRecordV1,
    TranscriptSequenceSnapshotV1,
    TranscriptSequenceSnapshotValidationRecordV1,
    TranscriptTargetabilityAlignmentPositionRecordV1,
    TranscriptTargetabilityEvidenceRecordV1,
    TranscriptTargetabilityGeneFailureRecordV1,
    TranscriptTargetabilityMismatchRecordV1,
    TranscriptTargetabilitySiteRecordV1,
    stable_id,
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_sirna_sequence(sequence: str) -> tuple[str, str]:
    original = sequence
    stripped = "".join(original.split()).upper()
    if not stripped:
        raise ValueError("siRNA sequence must not be empty")
    if set(stripped) - set("ACGTU"):
        raise ValueError("siRNA sequence contains unsupported bases or modification notation")
    alphabet = "RNA" if "U" in stripped and "T" not in stripped else "DNA"
    if "U" in stripped and "T" in stripped:
        raise ValueError("mixed RNA/DNA alphabet with both U and T is unsupported")
    return stripped.replace("U", "T"), alphabet


def reverse_complement(sequence: str) -> str:
    table = str.maketrans("ACGTUacgtu", "TGCAAtgcaa")
    return sequence.translate(table)[::-1].upper().replace("U", "T")


def build_targetability_site_id(
    *,
    sirna_id: str,
    canonical_transcript_id: str,
    transcript_version: str | None,
    transcript_start: int,
    guide_sequence_checksum: str,
    transcript_sequence_snapshot_id: str,
    cleavage_policy: CleavageCompatibilityPolicyV1,
    seed_policy: SeedMatchPolicyV1,
) -> str:
    return stable_id(
        "tt-site",
        sirna_id,
        canonical_transcript_id,
        transcript_version,
        transcript_start,
        guide_sequence_checksum,
        transcript_sequence_snapshot_id,
        cleavage_policy.fingerprint,
        seed_policy.fingerprint,
    )


def validate_sirna_sequence(
    *,
    sirna_id: str,
    reagent_name: str,
    guide_sequence: str,
    organism: str,
    assembly: str,
    guide_orientation: str = "guide_5p_to_3p",
    passenger_sequence: str | None = None,
    intended_target_gene_id: str | None = None,
    intended_target_transcript_ids: tuple[str, ...] = (),
    source_file: str | None = None,
    source_file_checksum: str | None = None,
    sequence_source: str = "configured_input",
    cleavage_policy: CleavageCompatibilityPolicyV1 | None = None,
    passenger_search_requested: bool = False,
) -> tuple[SiRNASequenceRecordV1, SiRNASequenceValidationRecordV1]:
    if guide_orientation != "guide_5p_to_3p":
        raise ValueError("guide orientation must be explicitly guide_5p_to_3p")
    guide_normalized, alphabet = normalize_sirna_sequence(guide_sequence)
    passenger_normalized = None
    passenger_status = "not_supplied"
    passenger_valid: bool | None = None
    if passenger_sequence is not None:
        passenger_normalized, _alphabet = normalize_sirna_sequence(passenger_sequence)
        passenger_status = "explicit"
        passenger_valid = True
    policy = cleavage_policy or CleavageCompatibilityPolicyV1()
    guide_length = len(guide_normalized)
    if guide_length < policy.guide_length_min:
        raise ValueError("guide length is below configured minimum")
    if guide_length > policy.guide_length_max:
        raise ValueError("guide length is above configured maximum")
    record = SiRNASequenceRecordV1(
        sirna_id=sirna_id,
        reagent_name=reagent_name,
        guide_sequence_original=guide_sequence,
        guide_sequence_normalized=guide_normalized,
        guide_length=guide_length,
        guide_alphabet=alphabet,  # type: ignore[arg-type]
        guide_orientation="guide_5p_to_3p",
        guide_strand_status="explicit",
        passenger_sequence_original=passenger_sequence,
        passenger_sequence_normalized=passenger_normalized,
        passenger_sequence_status=passenger_status,  # type: ignore[arg-type]
        intended_target_gene_id=intended_target_gene_id,
        intended_target_transcript_ids=intended_target_transcript_ids,
        organism=organism,
        assembly=assembly,
        sequence_source=sequence_source,
        source_file=source_file,
        source_file_checksum=source_file_checksum,
    )
    validation = SiRNASequenceValidationRecordV1(
        validation_id=stable_id("sirna-validation", sirna_id, guide_normalized),
        sirna_id=sirna_id,
        guide_valid=True,
        guide_length=guide_length,
        guide_length_min=policy.guide_length_min,
        guide_length_max=policy.guide_length_max,
        guide_length_status="valid",
        guide_reverse_complement=reverse_complement(guide_normalized),
        passenger_valid=passenger_valid,
        passenger_search_status="unsupported" if passenger_search_requested else "not_requested",
    )
    return record, validation


def load_transcript_sequence_snapshot(
    cache_dir: Path, snapshot_id: str, manifest_name: str = "manifest.json"
) -> tuple[TranscriptSequenceSnapshotV1, list[TranscriptSequenceRecordV1], Path]:
    snapshot_dir = cache_dir / snapshot_id
    manifest_path = snapshot_dir / manifest_name
    if not manifest_path.exists():
        raise RuntimeError(f"missing transcript sequence manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    records_name = str(manifest.get("records_artifact", "transcript_sequences.jsonl"))
    records_path = snapshot_dir / records_name
    if not records_path.exists():
        raise RuntimeError(f"missing transcript sequence records: {records_path}")
    actual_checksum = hashlib.sha256(records_path.read_bytes()).hexdigest()
    expected = str(manifest.get("sequence_file_checksum", "")).removeprefix("sha256:")
    if expected and expected != actual_checksum:
        raise RuntimeError("transcript sequence snapshot checksum mismatch")
    manifest["sequence_file_checksum"] = actual_checksum
    manifest.setdefault("transcript_count", len(records_path.read_text().splitlines()))
    snapshot = TranscriptSequenceSnapshotV1.model_validate(manifest)
    records = [
        TranscriptSequenceRecordV1.model_validate(json.loads(line))
        for line in records_path.read_text().splitlines()
        if line.strip()
    ]
    return snapshot, records, records_path


def validate_transcript_sequence_snapshot(
    *,
    snapshot: TranscriptSequenceSnapshotV1,
    records: list[TranscriptSequenceRecordV1],
    expected_organism: str,
    expected_assembly: str,
    expected_release: str | None,
    eligible_transcripts: dict[str, str],
    require_complete_sequences: bool = True,
) -> TranscriptSequenceSnapshotValidationRecordV1:
    seen: set[str] = set()
    duplicates: list[str] = []
    wrong_gene: list[str] = []
    invalid: list[str] = []
    by_transcript = {record.canonical_transcript_id: record for record in records}
    for record in records:
        if record.canonical_transcript_id in seen:
            duplicates.append(record.canonical_transcript_id)
        seen.add(record.canonical_transcript_id)
        if record.sequence_checksum and record.sequence_checksum != sha256_text(record.sequence):
            invalid.append(record.canonical_transcript_id)
        expected_gene = eligible_transcripts.get(record.canonical_transcript_id)
        if expected_gene is not None and expected_gene != record.canonical_gene_id:
            wrong_gene.append(record.canonical_transcript_id)
    missing = sorted(set(eligible_transcripts) - set(by_transcript))
    release_match = expected_release is None or snapshot.release == expected_release
    organism_match = snapshot.organism == expected_organism
    assembly_match = snapshot.assembly == expected_assembly
    fatal = []
    if snapshot.verification_status != "verified":
        fatal.append("sequence snapshot is not verified")
    if not release_match:
        fatal.append("annotation and sequence release mismatch")
    if not organism_match:
        fatal.append("organism mismatch")
    if not assembly_match:
        fatal.append("assembly mismatch")
    fatal.extend(f"duplicate sequence id:{item}" for item in duplicates)
    fatal.extend(f"wrong gene assignment:{item}" for item in wrong_gene)
    if require_complete_sequences:
        fatal.extend(f"missing eligible transcript:{item}" for item in missing)
    fatal.extend(f"invalid sequence checksum:{item}" for item in invalid)
    return TranscriptSequenceSnapshotValidationRecordV1(
        validation_id=stable_id("tx-sequence-validation", snapshot.snapshot_id),
        snapshot_id=snapshot.snapshot_id,
        provider_release_match=release_match,
        organism_match=organism_match,
        assembly_match=assembly_match,
        transcript_namespace_match=True,
        duplicate_sequence_ids=tuple(duplicates),
        missing_eligible_transcripts=tuple(missing),
        wrong_gene_assignments=tuple(wrong_gene),
        invalid_sequence_ids=tuple(invalid),
        sequence_count=len(records),
        verification_status="verified" if not fatal else "failed",
        fatal_errors=tuple(fatal),
    )


def _region(position: int, cleavage: CleavageCompatibilityPolicyV1) -> str:
    if cleavage.seed_start <= position <= cleavage.seed_end:
        return "seed"
    if cleavage.central_region_start <= position <= cleavage.central_region_end:
        return "central"
    if position <= 1 or position > cleavage.supplementary_region[1]:
        return "terminal"
    return "nonseed"


def _classify_site(
    *,
    total: int,
    seed: int,
    central: int,
    nonseed: int,
    guide_length: int,
    matched_bases: int,
    cleavage: CleavageCompatibilityPolicyV1,
    seed_policy: SeedMatchPolicyV1,
) -> tuple[str, str, str, int]:
    if total == 0:
        return (
            "exact_full_length_complement",
            "cleavage_compatible_candidate",
            "not_seed_only",
            0,
        )
    if (
        total <= cleavage.maximum_total_mismatches
        and seed <= cleavage.maximum_seed_mismatches
        and central <= cleavage.maximum_central_mismatches
        and nonseed <= cleavage.maximum_nonseed_mismatches
    ):
        return (
            "near_full_length_complement",
            "cleavage_compatible_candidate",
            "not_seed_only",
            1,
        )
    if (
        seed <= seed_policy.allowed_seed_mismatches
        and total <= seed_policy.maximum_total_mismatches
        and matched_bases >= seed_policy.minimum_total_paired_bases
    ):
        return ("seed_only_candidate", "not_cleavage_compatible", "seed_only_candidate", 3)
    if total < guide_length:
        return ("partial_nonseed_match", "not_cleavage_compatible", "not_seed_only", 4)
    return ("unsupported_alignment", "not_cleavage_compatible", "not_seed_only", 9)


def find_transcript_targetability(
    *,
    sirna: SiRNASequenceRecordV1,
    transcript: TranscriptSequenceRecordV1,
    transcript_prior_weight: float | None,
    source_isoform_uncertainty_record_id: str,
    source_transcript_weight_record_id: str,
    transcript_sequence_snapshot_id: str,
    cleavage_policy: CleavageCompatibilityPolicyV1 | None = None,
    seed_policy: SeedMatchPolicyV1 | None = None,
) -> tuple[
    TranscriptTargetabilityEvidenceRecordV1,
    list[TranscriptTargetabilitySiteRecordV1],
    list[TranscriptTargetabilityMismatchRecordV1],
    list[TranscriptTargetabilityAlignmentPositionRecordV1],
]:
    cleavage = cleavage_policy or CleavageCompatibilityPolicyV1()
    seed = seed_policy or SeedMatchPolicyV1()
    guide_search = reverse_complement(sirna.guide_sequence_normalized)
    sites: list[TranscriptTargetabilitySiteRecordV1] = []
    mismatches: list[TranscriptTargetabilityMismatchRecordV1] = []
    positions: list[TranscriptTargetabilityAlignmentPositionRecordV1] = []
    if len(transcript.sequence) < len(guide_search):
        return (
            _empty_evidence(
                sirna=sirna,
                transcript=transcript,
                transcript_prior_weight=transcript_prior_weight,
                source_isoform_uncertainty_record_id=source_isoform_uncertainty_record_id,
                source_transcript_weight_record_id=source_transcript_weight_record_id,
            ),
            [],
            [],
            [],
        )
    for start in range(0, len(transcript.sequence) - len(guide_search) + 1):
        site_seq = transcript.sequence[start : start + len(guide_search)]
        mismatch_positions: list[int] = []
        seed_mismatches = 0
        central_mismatches = 0
        nonseed_mismatches = 0
        site_mismatches: list[TranscriptTargetabilityMismatchRecordV1] = []
        site_positions: list[TranscriptTargetabilityAlignmentPositionRecordV1] = []
        site_id_placeholder = build_targetability_site_id(
            sirna_id=sirna.sirna_id,
            canonical_transcript_id=transcript.canonical_transcript_id,
            transcript_version=transcript.transcript_version,
            transcript_start=start,
            guide_sequence_checksum=sha256_text(sirna.guide_sequence_normalized),
            transcript_sequence_snapshot_id=transcript_sequence_snapshot_id,
            cleavage_policy=cleavage,
            seed_policy=seed,
        )
        for index, (guide_base, target_base) in enumerate(
            zip(guide_search, site_seq, strict=True), start=1
        ):
            region = _region(index, cleavage)
            is_mismatch = guide_base != target_base
            if is_mismatch:
                mismatch_positions.append(index)
                seed_mismatches += int(region == "seed")
                central_mismatches += int(region == "central")
                nonseed_mismatches += int(region not in {"seed", "central"})
                site_mismatches.append(
                    TranscriptTargetabilityMismatchRecordV1(
                        mismatch_record_id=stable_id("tt-mismatch", site_id_placeholder, index),
                        site_record_id=site_id_placeholder,
                        guide_position=index,
                        target_position=start + index - 1,
                        guide_base=guide_base,
                        target_paired_base=target_base,
                        mismatch_region=region,  # type: ignore[arg-type]
                        mismatch_type=f"{guide_base}>{target_base}",
                        seed_membership=region == "seed",
                        central_region_membership=region == "central",
                        terminal_region_membership=region == "terminal",
                    )
                )
            site_positions.append(
                TranscriptTargetabilityAlignmentPositionRecordV1(
                    position_record_id=stable_id("tt-position", site_id_placeholder, index),
                    site_record_id=site_id_placeholder,
                    guide_position=index,
                    transcript_position=start + index - 1,
                    guide_base=guide_base,
                    target_base=target_base,
                    pairing_status="mismatch" if is_mismatch else "match",
                    seed_membership=region == "seed",
                    central_membership=region == "central",
                    terminal_membership=region == "terminal",
                )
            )
        total = len(mismatch_positions)
        matched_bases = len(guide_search) - total
        evidence_class, cleavage_status, seed_status, priority = _classify_site(
            total=total,
            seed=seed_mismatches,
            central=central_mismatches,
            nonseed=nonseed_mismatches,
            guide_length=len(guide_search),
            matched_bases=matched_bases,
            cleavage=cleavage,
            seed_policy=seed,
        )
        if evidence_class == "unsupported_alignment":
            continue
        site_id = build_targetability_site_id(
            sirna_id=sirna.sirna_id,
            canonical_transcript_id=transcript.canonical_transcript_id,
            transcript_version=transcript.transcript_version,
            transcript_start=start,
            guide_sequence_checksum=sha256_text(sirna.guide_sequence_normalized),
            transcript_sequence_snapshot_id=transcript_sequence_snapshot_id,
            cleavage_policy=cleavage,
            seed_policy=seed,
        )
        fixed_mismatches = [
            item.model_copy(update={"site_record_id": site_id}) for item in site_mismatches
        ]
        fixed_positions = [
            item.model_copy(update={"site_record_id": site_id}) for item in site_positions
        ]
        site = TranscriptTargetabilitySiteRecordV1(
            site_record_id=site_id,
            sirna_id=sirna.sirna_id,
            source_isoform_uncertainty_record_id=source_isoform_uncertainty_record_id,
            source_transcript_weight_record_id=source_transcript_weight_record_id,
            canonical_gene_id=transcript.canonical_gene_id,
            canonical_transcript_id=transcript.canonical_transcript_id,
            transcript_version=transcript.transcript_version,
            transcript_sequence_snapshot_id=transcript_sequence_snapshot_id,
            transcript_sequence_checksum=sha256_text(transcript.sequence),
            guide_sequence_record_id=sirna.sirna_id,
            guide_search_sequence=guide_search,
            transcript_site_sequence=site_seq,
            alignment_orientation="guide_reverse_complement_to_transcript_5p_to_3p",
            transcript_start=start,
            transcript_end=start + len(guide_search),
            alignment_length=len(guide_search),
            matched_base_count=matched_bases,
            minimum_total_paired_bases=seed.minimum_total_paired_bases,
            paired_base_policy_status="passed"
            if matched_bases >= seed.minimum_total_paired_bases
            else "failed",
            total_mismatch_count=total,
            seed_mismatch_count=seed_mismatches,
            central_mismatch_count=central_mismatches,
            nonseed_mismatch_count=nonseed_mismatches,
            mismatch_positions=tuple(mismatch_positions),
            seed_match_status="exact_seed" if seed_mismatches == 0 else "seed_mismatch",
            supplementary_pairing_status="recorded_not_required",
            evidence_class=evidence_class,  # type: ignore[arg-type]
            cleavage_compatibility_status=cleavage_status,  # type: ignore[arg-type]
            seed_only_status=seed_status,  # type: ignore[arg-type]
            alignment_score=len(guide_search) - total,
            ranking_tuple=(priority, total, seed_mismatches, central_mismatches, start),
        )
        sites.append(site)
        mismatches.extend(fixed_mismatches)
        positions.extend(fixed_positions)
    sites.sort(key=lambda item: item.ranking_tuple)
    evidence = _evidence_from_sites(
        sirna=sirna,
        transcript=transcript,
        transcript_prior_weight=transcript_prior_weight,
        source_isoform_uncertainty_record_id=source_isoform_uncertainty_record_id,
        source_transcript_weight_record_id=source_transcript_weight_record_id,
        sites=sites,
    )
    return evidence, sites, mismatches, positions


def unavailable_sequence_evidence(
    *,
    sirna: SiRNASequenceRecordV1,
    canonical_gene_id: str,
    canonical_transcript_id: str,
    transcript_version: str | None,
    transcript_prior_weight: float | None,
    source_isoform_uncertainty_record_id: str,
    source_transcript_weight_record_id: str,
) -> TranscriptTargetabilityEvidenceRecordV1:
    return TranscriptTargetabilityEvidenceRecordV1(
        evidence_record_id=stable_id("tt-evidence", sirna.sirna_id, canonical_transcript_id),
        sirna_id=sirna.sirna_id,
        canonical_gene_id=canonical_gene_id,
        canonical_transcript_id=canonical_transcript_id,
        transcript_version=transcript_version,
        source_isoform_uncertainty_record_id=source_isoform_uncertainty_record_id,
        source_transcript_weight_record_id=source_transcript_weight_record_id,
        transcript_prior_weight=transcript_prior_weight,
        sequence_available=False,
        sites_examined=0,
        qualifying_site_count=0,
        exact_site_count=0,
        near_full_length_site_count=0,
        cleavage_candidate_site_count=0,
        seed_only_site_count=0,
        partial_match_site_count=0,
        evidence_status="sequence_unavailable",
        targetability_decision_status="sequence_unavailable",
        targetability_decision_reason="transcript sequence unavailable under explicit policy",
    )


def gene_failed_evidence(
    *,
    sirna: SiRNASequenceRecordV1,
    canonical_gene_id: str,
    canonical_transcript_id: str,
    transcript_version: str | None,
    transcript_prior_weight: float | None,
    source_isoform_uncertainty_record_id: str,
    source_transcript_weight_record_id: str,
    triggering_transcript_ids: tuple[str, ...],
) -> TranscriptTargetabilityEvidenceRecordV1:
    return TranscriptTargetabilityEvidenceRecordV1(
        evidence_record_id=stable_id(
            "tt-evidence-gene-failed", sirna.sirna_id, canonical_transcript_id
        ),
        sirna_id=sirna.sirna_id,
        canonical_gene_id=canonical_gene_id,
        canonical_transcript_id=canonical_transcript_id,
        transcript_version=transcript_version,
        source_isoform_uncertainty_record_id=source_isoform_uncertainty_record_id,
        source_transcript_weight_record_id=source_transcript_weight_record_id,
        transcript_prior_weight=transcript_prior_weight,
        sequence_available=False,
        sites_examined=0,
        qualifying_site_count=0,
        exact_site_count=0,
        near_full_length_site_count=0,
        cleavage_candidate_site_count=0,
        seed_only_site_count=0,
        partial_match_site_count=0,
        evidence_status="not_evaluated_due_to_gene_failure",
        targetability_decision_status="not_evaluated_due_to_gene_failure",
        targetability_decision_reason=(
            "gene failed under missing transcript sequence policy; triggering transcripts: "
            + ",".join(triggering_transcript_ids)
        ),
    )


def build_gene_failure_record(
    *,
    canonical_gene_id: str,
    affected_transcript_ids: tuple[str, ...],
    triggering_transcript_ids: tuple[str, ...],
    missing_sequence_policy_id: str,
    source_isoform_uncertainty_record_ids: tuple[str, ...],
) -> TranscriptTargetabilityGeneFailureRecordV1:
    return TranscriptTargetabilityGeneFailureRecordV1(
        failure_record_id=stable_id(
            "tt-gene-failure",
            canonical_gene_id,
            affected_transcript_ids,
            triggering_transcript_ids,
            missing_sequence_policy_id,
        ),
        canonical_gene_id=canonical_gene_id,
        affected_transcript_ids=affected_transcript_ids,
        triggering_transcript_ids=triggering_transcript_ids,
        failure_reason="gene_failed_missing_transcript_sequence",
        missing_sequence_policy_id=missing_sequence_policy_id,
        source_isoform_uncertainty_record_ids=source_isoform_uncertainty_record_ids,
    )


def validate_intended_target_actual_site(
    *,
    intended_target_gene_id: str | None = None,
    intended_transcript_ids: tuple[str, ...],
    evidence_records: list[TranscriptTargetabilityEvidenceRecordV1],
    site_records: list[TranscriptTargetabilitySiteRecordV1],
    gene_failure_records: list[TranscriptTargetabilityGeneFailureRecordV1] | None = None,
    policy: IntendedTargetValidationPolicyV1 | None = None,
) -> IntendedTargetValidationRecordV1:
    active_policy = policy or IntendedTargetValidationPolicyV1()
    failed_genes = {record.canonical_gene_id for record in gene_failure_records or []}
    sites_by_id = {site.site_record_id: site for site in site_records}
    candidate_site_ids: list[str] = []
    accepted_site_ids: list[str] = []
    rejected_site_ids: list[str] = []
    rejection_reasons: dict[str, tuple[str, ...]] = {}
    mismatch_checks: dict[str, str] = {}
    evidence_class_checks: dict[str, str] = {}
    sequence_checks: dict[str, str] = {}
    gene_failure_checks: dict[str, str] = {}
    warnings: list[str] = list(active_policy.warnings)
    errors: list[str] = []

    supplied_status = (
        "transcript_ids_supplied"
        if intended_transcript_ids
        else "gene_only"
        if intended_target_gene_id
        else "missing_required"
    )

    if (
        not active_policy.intended_target_required
        and not intended_target_gene_id
        and not intended_transcript_ids
    ):
        return IntendedTargetValidationRecordV1(
            validation_record_id=stable_id("intended-target-validation", active_policy.policy_id),
            policy_id=active_policy.policy_id,
            intended_target_required=active_policy.intended_target_required,
            transcript_ids_required=active_policy.transcript_ids_required,
            intended_target_gene_id=intended_target_gene_id,
            intended_target_transcript_ids=intended_transcript_ids,
            supplied_input_status="not_requested",
            gene_only_behavior=active_policy.gene_only_behavior,
            validation_status="not_requested",
        )

    if active_policy.intended_target_required and supplied_status == "missing_required":
        errors.append("intended_target_input_missing")
    if active_policy.transcript_ids_required and not intended_transcript_ids:
        errors.append("intended_target_transcript_ids_required")
    if intended_target_gene_id in failed_genes:
        errors.append(f"intended_target_gene_failed:{intended_target_gene_id}")
        if intended_target_gene_id is not None:
            gene_failure_checks[intended_target_gene_id] = "failed_gene"

    evidence_by_tx = {record.canonical_transcript_id: record for record in evidence_records}
    for transcript_id in intended_transcript_ids:
        evidence = evidence_by_tx.get(transcript_id)
        if evidence is None:
            errors.append(f"intended_target_transcript_missing:{transcript_id}")
            sequence_checks[transcript_id] = "missing_evidence"
            continue
        if evidence.canonical_gene_id in failed_genes:
            errors.append(f"intended_target_gene_failed:{evidence.canonical_gene_id}")
            gene_failure_checks[evidence.canonical_gene_id] = "failed_gene"
            continue
        if not evidence.sequence_available:
            errors.append(f"intended_target_sequence_unavailable:{transcript_id}")
            sequence_checks[transcript_id] = "unavailable"
            continue
        sequence_checks[transcript_id] = "available"
        candidate_site_ids.extend(evidence.site_record_ids)

    if not intended_transcript_ids and intended_target_gene_id:
        if active_policy.gene_only_behavior == "fail_stage":
            errors.append("gene_only_intended_target_not_allowed")
        elif active_policy.gene_only_behavior in {"warning", "preserve_uncertainty"}:
            warnings.append(
                "intended target supplied only at gene level; isoform identity unresolved"
            )
        elif active_policy.gene_only_behavior == "accept_any_gene_transcript_site":
            gene_records = [
                record
                for record in evidence_records
                if record.canonical_gene_id == intended_target_gene_id
                and record.targetability_decision_status
                not in {"sequence_unavailable", "not_evaluated_due_to_gene_failure"}
            ]
            for record in gene_records:
                candidate_site_ids.extend(record.site_record_ids)

    for site_id in candidate_site_ids:
        site = sites_by_id.get(site_id)
        reasons: list[str] = []
        if site is None:
            reasons.append("site_record_missing")
        else:
            if site.evidence_class not in active_policy.accepted_evidence_classes:
                reasons.append("evidence_class_not_accepted")
            if site.total_mismatch_count > active_policy.maximum_total_mismatches:
                reasons.append("total_mismatch_threshold_exceeded")
            if site.seed_mismatch_count > active_policy.maximum_seed_mismatches:
                reasons.append("seed_mismatch_threshold_exceeded")
            if site.central_mismatch_count > active_policy.maximum_central_mismatches:
                reasons.append("central_mismatch_threshold_exceeded")
        if reasons:
            rejected_site_ids.append(site_id)
            rejection_reasons[site_id] = tuple(reasons)
            evidence_class_checks[site_id] = "failed"
            mismatch_checks[site_id] = "failed"
        else:
            accepted_site_ids.append(site_id)
            evidence_class_checks[site_id] = "passed"
            mismatch_checks[site_id] = "passed"

    if (
        intended_transcript_ids
        or active_policy.gene_only_behavior == "accept_any_gene_transcript_site"
    ) and (candidate_site_ids and not accepted_site_ids):
        errors.append("intended_target_no_acceptable_site")
    if (
        active_policy.gene_only_behavior == "accept_any_gene_transcript_site"
        and intended_target_gene_id
        and not candidate_site_ids
    ):
        errors.append(f"intended_target_gene_no_acceptable_site:{intended_target_gene_id}")

    if errors:
        if active_policy.failure_behavior == "warning":
            status = "warning"
            behavior = "warning"
        elif active_policy.failure_behavior == "preserve_invalid_with_status":
            status = "invalid_preserved"
            behavior = "preserve_invalid_with_status"
        else:
            status = "failed"
            behavior = "fail_stage"
    elif accepted_site_ids:
        status = "passed"
        behavior = "none"
    elif supplied_status == "gene_only" and active_policy.gene_only_behavior == "warning":
        status = "warning"
        behavior = "warning"
    elif (
        supplied_status == "gene_only"
        and active_policy.gene_only_behavior == "preserve_uncertainty"
    ):
        status = "uncertain"
        behavior = "none"
    else:
        status = "passed"
        behavior = "none"

    best_accepted_site_id = None
    if accepted_site_ids:
        best_accepted_site_id = sorted(
            (sites_by_id[site_id] for site_id in accepted_site_ids),
            key=lambda item: item.ranking_tuple,
        )[0].site_record_id
    return IntendedTargetValidationRecordV1(
        validation_record_id=stable_id(
            "intended-target-validation",
            active_policy.policy_id,
            intended_target_gene_id,
            intended_transcript_ids,
        ),
        policy_id=active_policy.policy_id,
        intended_target_required=active_policy.intended_target_required,
        transcript_ids_required=active_policy.transcript_ids_required,
        intended_target_gene_id=intended_target_gene_id,
        intended_target_transcript_ids=intended_transcript_ids,
        supplied_input_status=supplied_status,  # type: ignore[arg-type]
        gene_only_behavior=active_policy.gene_only_behavior,
        candidate_site_ids=tuple(candidate_site_ids),
        accepted_site_ids=tuple(accepted_site_ids),
        rejected_site_ids=tuple(rejected_site_ids),
        rejection_reasons=rejection_reasons,
        best_accepted_site_id=best_accepted_site_id,
        mismatch_threshold_checks=mismatch_checks,
        evidence_class_checks=evidence_class_checks,
        sequence_availability_checks=sequence_checks,
        gene_failure_checks=gene_failure_checks,
        validation_status=status,  # type: ignore[arg-type]
        failure_behavior_applied=behavior,  # type: ignore[arg-type]
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def _empty_evidence(
    *,
    sirna: SiRNASequenceRecordV1,
    transcript: TranscriptSequenceRecordV1,
    transcript_prior_weight: float | None,
    source_isoform_uncertainty_record_id: str,
    source_transcript_weight_record_id: str,
) -> TranscriptTargetabilityEvidenceRecordV1:
    return TranscriptTargetabilityEvidenceRecordV1(
        evidence_record_id=stable_id(
            "tt-evidence", sirna.sirna_id, transcript.canonical_transcript_id
        ),
        sirna_id=sirna.sirna_id,
        canonical_gene_id=transcript.canonical_gene_id,
        canonical_transcript_id=transcript.canonical_transcript_id,
        transcript_version=transcript.transcript_version,
        source_isoform_uncertainty_record_id=source_isoform_uncertainty_record_id,
        source_transcript_weight_record_id=source_transcript_weight_record_id,
        transcript_prior_weight=transcript_prior_weight,
        sequence_available=True,
        sites_examined=0,
        qualifying_site_count=0,
        exact_site_count=0,
        near_full_length_site_count=0,
        cleavage_candidate_site_count=0,
        seed_only_site_count=0,
        partial_match_site_count=0,
        evidence_status="no_supported_site",
        targetability_decision_status="no_supported_site",
        targetability_decision_reason="no supported ungapped guide-complement site found",
    )


def _evidence_from_sites(
    *,
    sirna: SiRNASequenceRecordV1,
    transcript: TranscriptSequenceRecordV1,
    transcript_prior_weight: float | None,
    source_isoform_uncertainty_record_id: str,
    source_transcript_weight_record_id: str,
    sites: list[TranscriptTargetabilitySiteRecordV1],
) -> TranscriptTargetabilityEvidenceRecordV1:
    if not sites:
        return _empty_evidence(
            sirna=sirna,
            transcript=transcript,
            transcript_prior_weight=transcript_prior_weight,
            source_isoform_uncertainty_record_id=source_isoform_uncertainty_record_id,
            source_transcript_weight_record_id=source_transcript_weight_record_id,
        )
    exact = sum(site.evidence_class == "exact_full_length_complement" for site in sites)
    near = sum(site.evidence_class == "near_full_length_complement" for site in sites)
    cleavage = sum(
        site.cleavage_compatibility_status == "cleavage_compatible_candidate" for site in sites
    )
    seed_only = sum(site.evidence_class == "seed_only_candidate" for site in sites)
    partial = sum(site.evidence_class == "partial_nonseed_match" for site in sites)
    best = sites[0]
    tied = sum(site.ranking_tuple == best.ranking_tuple for site in sites) > 1
    if cleavage:
        status = "cleavage_candidate_present"
    elif seed_only:
        status = "seed_only_candidate_present"
    else:
        status = "indeterminate"
    return TranscriptTargetabilityEvidenceRecordV1(
        evidence_record_id=stable_id(
            "tt-evidence", sirna.sirna_id, transcript.canonical_transcript_id
        ),
        sirna_id=sirna.sirna_id,
        canonical_gene_id=transcript.canonical_gene_id,
        canonical_transcript_id=transcript.canonical_transcript_id,
        transcript_version=transcript.transcript_version,
        source_isoform_uncertainty_record_id=source_isoform_uncertainty_record_id,
        source_transcript_weight_record_id=source_transcript_weight_record_id,
        transcript_prior_weight=transcript_prior_weight,
        sequence_available=True,
        sites_examined=len(sites),
        qualifying_site_count=len(sites),
        exact_site_count=exact,
        near_full_length_site_count=near,
        cleavage_candidate_site_count=cleavage,
        seed_only_site_count=seed_only,
        partial_match_site_count=partial,
        best_site_record_id=best.site_record_id,
        site_record_ids=tuple(site.site_record_id for site in sites),
        evidence_status=status,  # type: ignore[arg-type]
        targetability_decision_status=status,  # type: ignore[arg-type]
        targetability_decision_reason=(
            "sequence compatibility evidence only; no aggregate fraction computed"
        ),
        tie_status="tied_best_sites" if tied else "none",
    )


def utc_now() -> str:
    return datetime.now(UTC).isoformat()
