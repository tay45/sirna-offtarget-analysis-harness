from __future__ import annotations

import math
from collections import Counter

from sirna_offtarget.isoform_uncertainty.contracts import (
    ExternalProportionPolicy,
    ExternalTranscriptProportionPolicyV1,
    ExternalTranscriptProportionRecordV1,
    GeneIsoformUncertaintyRecordV1,
    IsoformEvidenceMode,
    IsoformResolutionStatus,
    TranscriptAnnotationRecordV1,
    TranscriptAnnotationSnapshotV1,
    TranscriptAnnotationValidationRecordV1,
    TranscriptPriorWeightRecordV1,
    TranscriptSetExclusionRecordV1,
    TranscriptSetPolicyV1,
    TranscriptWeightType,
    stable_id,
)


class IsoformUncertaintyPolicyError(RuntimeError):
    pass


def validate_annotation_snapshot(
    snapshot: TranscriptAnnotationSnapshotV1,
    records: list[TranscriptAnnotationRecordV1],
    *,
    require_verified: bool = True,
) -> TranscriptAnnotationValidationRecordV1:
    transcript_counts = Counter(record.original_transcript_id for record in records)
    duplicates = sum(1 for count in transcript_counts.values() if count > 1)
    organism_conflicts = sum(record.organism != snapshot.organism for record in records)
    assembly_conflicts = sum(record.assembly != snapshot.assembly for record in records)
    unresolved_genes = sum(record.canonical_gene_id is None for record in records)
    unresolved_transcripts = sum(record.canonical_transcript_id is None for record in records)
    missing_sequence = sum(record.sequence_reference is None for record in records)
    fatal_errors: list[str] = []
    if require_verified and snapshot.verification_status != "verified":
        fatal_errors.append("annotation snapshot is not verified")
    if organism_conflicts:
        fatal_errors.append("annotation organism conflicts with snapshot")
    if assembly_conflicts:
        fatal_errors.append("annotation assembly conflicts with snapshot")
    if duplicates:
        fatal_errors.append("duplicate transcript identifiers present")
    return TranscriptAnnotationValidationRecordV1(
        annotation_snapshot_id=snapshot.snapshot_id,
        total_rows=len(records),
        unique_genes=len(
            {record.canonical_gene_id for record in records if record.canonical_gene_id}
        ),
        unique_transcripts=len(transcript_counts),
        duplicates=duplicates,
        invalid_mappings=unresolved_genes + unresolved_transcripts,
        unresolved_genes=unresolved_genes,
        unresolved_transcripts=unresolved_transcripts,
        assembly_conflicts=assembly_conflicts,
        organism_conflicts=organism_conflicts,
        missing_sequence_references=missing_sequence,
        fatal_errors=tuple(fatal_errors),
    )


def _exclusion_reason(
    record: TranscriptAnnotationRecordV1,
    snapshot: TranscriptAnnotationSnapshotV1,
    policy: TranscriptSetPolicyV1,
) -> str | None:
    if record.organism != snapshot.organism:
        return "organism_mismatch"
    if record.assembly != snapshot.assembly:
        return "assembly_mismatch"
    if record.canonical_gene_id is None or record.unresolved_gene_mapping:
        return "unresolved_gene_mapping"
    if record.canonical_transcript_id is None:
        return "unresolved_transcript_mapping"
    if record.ambiguous_transcript_mapping:
        return "ambiguous_transcript_mapping"
    if policy.require_sequence_reference and record.sequence_reference is None:
        return "missing_sequence_reference"
    if record.deprecated and not policy.allow_deprecated_transcripts:
        return "deprecated_transcript"
    if record.alternative_contig and not policy.allow_alternative_contigs:
        return "alternative_contig"
    if record.transcript_biotype == "protein_coding" and not policy.include_protein_coding:
        return "protein_coding_excluded"
    if record.transcript_biotype == "retained_intron" and not policy.include_retained_intron:
        return "retained_intron_excluded"
    if (
        record.transcript_biotype == "nonsense_mediated_decay"
        and not policy.include_nonsense_mediated_decay
    ):
        return "nonsense_mediated_decay_excluded"
    if (
        record.transcript_biotype == "processed_transcript"
        and not policy.include_processed_transcript
    ):
        return "processed_transcript_excluded"
    if record.transcript_biotype.endswith("pseudogene") and not policy.include_pseudogene:
        return "pseudogene_transcript_excluded"
    if record.transcript_biotype == "readthrough_transcript" and not policy.include_readthrough:
        return "readthrough_transcript_excluded"
    if (
        record.transcript_biotype
        not in {
            "protein_coding",
            "retained_intron",
            "nonsense_mediated_decay",
            "processed_transcript",
            "readthrough_transcript",
        }
        and not record.transcript_biotype.endswith("pseudogene")
        and not policy.include_noncoding
    ):
        return "noncoding_transcript_excluded"
    if (
        policy.allowed_transcript_support_levels is not None
        and record.transcript_support_level not in policy.allowed_transcript_support_levels
    ):
        return "transcript_support_level_excluded"
    return None


def _eligible_and_excluded(
    canonical_gene_id: str,
    records: list[TranscriptAnnotationRecordV1],
    snapshot: TranscriptAnnotationSnapshotV1,
    policy: TranscriptSetPolicyV1,
) -> tuple[list[TranscriptAnnotationRecordV1], list[TranscriptSetExclusionRecordV1]]:
    gene_records = [
        record
        for record in records
        if record.canonical_gene_id == canonical_gene_id
        or record.original_gene_id == canonical_gene_id
    ]
    eligible: list[TranscriptAnnotationRecordV1] = []
    exclusions: list[TranscriptSetExclusionRecordV1] = []
    for record in sorted(gene_records, key=lambda item: item.original_transcript_id):
        reason = _exclusion_reason(record, snapshot, policy)
        if reason is None:
            eligible.append(record)
            continue
        transcript_id = record.canonical_transcript_id or record.original_transcript_id
        exclusions.append(
            TranscriptSetExclusionRecordV1(
                record_id=stable_id(
                    "tx-exclusion",
                    snapshot.snapshot_id,
                    policy.fingerprint,
                    canonical_gene_id,
                    transcript_id,
                    reason,
                ),
                canonical_gene_id=canonical_gene_id,
                transcript_id=transcript_id,
                policy_id=policy.policy_id,
                exclusion_reason=reason,
                annotation_snapshot_id=snapshot.snapshot_id,
                warnings=record.warnings,
            )
        )
    return eligible, exclusions


def build_equal_prior_weights(
    *,
    gene_record_id: str,
    original_gene_id: str,
    canonical_gene_id: str,
    eligible_transcripts: list[TranscriptAnnotationRecordV1],
    tolerance: float = 1e-9,
) -> tuple[list[TranscriptPriorWeightRecordV1], float]:
    if not eligible_transcripts:
        return [], 0.0
    weight = 1.0 / len(eligible_transcripts)
    weights = [
        TranscriptPriorWeightRecordV1(
            record_id=stable_id(
                "tx-weight",
                gene_record_id,
                record.original_transcript_id,
                record.canonical_transcript_id,
                "equal_prior",
            ),
            gene_isoform_uncertainty_record_id=gene_record_id,
            original_gene_id=original_gene_id,
            canonical_gene_id=canonical_gene_id,
            original_transcript_id=record.original_transcript_id,
            canonical_transcript_id=record.canonical_transcript_id or record.original_transcript_id,
            transcript_version=record.transcript_version,
            transcript_biotype=record.transcript_biotype,
            annotation_status="annotation_eligible",
            eligibility_status="eligible",
            exclusion_reason=None,
            weight=weight,
            weight_type="equal_prior",
            weight_source="annotation_only_equal_prior",
            weight_evidence_status="assumption_due_to_unresolved_isoform_abundance",
            source_annotation_release=record.annotation_release,
            warnings=(
                "equal transcript prior is a neutral fallback, not measured transcript abundance",
            ),
        )
        for record in sorted(eligible_transcripts, key=lambda item: item.original_transcript_id)
    ]
    total = sum(item.weight or 0.0 for item in weights)
    if abs(total - 1.0) > tolerance:
        raise ValueError("equal-prior weights do not sum to 1 within tolerance")
    return weights, total


def validate_external_proportions(
    *,
    proportions: list[ExternalTranscriptProportionRecordV1],
    eligible_transcripts: list[TranscriptAnnotationRecordV1],
    snapshot: TranscriptAnnotationSnapshotV1,
    tolerance: float = 1e-6,
    policy: ExternalProportionPolicy | ExternalTranscriptProportionPolicyV1 = "fail_gene",
) -> tuple[bool, tuple[str, ...], float]:
    proportion_policy = (
        policy
        if isinstance(policy, ExternalTranscriptProportionPolicyV1)
        else ExternalTranscriptProportionPolicyV1(invalid_proportion_behavior=policy)
    )
    eligible_by_transcript = {
        record.canonical_transcript_id or record.original_transcript_id: record
        for record in eligible_transcripts
    }
    supplied_transcripts = {item.canonical_transcript_id for item in proportions}
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    total = 0.0
    for item in proportions:
        key = (item.canonical_gene_id, item.canonical_transcript_id)
        if key in seen:
            errors.append("duplicate_gene_transcript_row")
        seen.add(key)
        total += item.proportion
        if item.organism != snapshot.organism:
            errors.append("organism_mismatch")
        if item.assembly != snapshot.assembly:
            errors.append("assembly_mismatch")
        if item.annotation_release != snapshot.release:
            errors.append("annotation_release_mismatch")
        transcript = eligible_by_transcript.get(item.canonical_transcript_id)
        if transcript is None:
            errors.append("transcript_not_eligible_for_gene")
        elif transcript.canonical_gene_id != item.canonical_gene_id:
            errors.append("wrong_gene_transcript_mapping")
    missing = set(eligible_by_transcript) - supplied_transcripts
    if missing and proportion_policy.missing_transcript_behavior in {
        "require_complete_coverage",
        "fallback_to_equal_prior",
    }:
        errors.append("missing_transcript_proportion")
    if abs(total - 1.0) > tolerance:
        errors.append("proportion_sum_outside_tolerance")
    if errors and proportion_policy.invalid_proportion_behavior == "renormalize_with_warning":
        can_renormalize = (
            proportion_policy.allow_renormalization
            and set(errors).issubset({"proportion_sum_outside_tolerance"})
            and total > 0
            and abs(total - 1.0) <= proportion_policy.material_sum_tolerance
        )
        if can_renormalize:
            errors = []
        else:
            errors.append("renormalization_requires_explicit_materiality_review")
    return not errors, tuple(dict.fromkeys(errors)), total


def _external_weight_records(
    *,
    gene_record_id: str,
    original_gene_id: str,
    canonical_gene_id: str,
    eligible_transcripts: list[TranscriptAnnotationRecordV1],
    proportions: list[ExternalTranscriptProportionRecordV1],
    tolerance: float,
    external_policy: ExternalTranscriptProportionPolicyV1 | None = None,
) -> tuple[list[TranscriptPriorWeightRecordV1], float]:
    external_policy = external_policy or ExternalTranscriptProportionPolicyV1()
    by_transcript = {item.canonical_transcript_id: item for item in proportions}
    supplied_total = sum(item.proportion for item in proportions)
    scale = 1.0
    renormalized = False
    if (
        external_policy.invalid_proportion_behavior == "renormalize_with_warning"
        and external_policy.allow_renormalization
        and supplied_total > 0
        and not math.isclose(supplied_total, 1.0, abs_tol=tolerance)
    ):
        scale = 1.0 / supplied_total
        renormalized = True
    weights: list[TranscriptPriorWeightRecordV1] = []
    for record in sorted(eligible_transcripts, key=lambda item: item.original_transcript_id):
        transcript_id = record.canonical_transcript_id or record.original_transcript_id
        external = by_transcript.get(transcript_id)
        if external is None:
            if external_policy.missing_transcript_behavior == "missing_as_zero":
                weight = 0.0
                weight_type: TranscriptWeightType = "external_proportion"
                evidence_status = "external_proportion_missing_treated_as_zero_by_policy"
            else:
                weight = None
                weight_type = "unavailable"
                evidence_status = "external_proportion_missing_for_transcript"
        else:
            weight = external.proportion * scale
            weight_type = "external_proportion"
            evidence_status = (
                "externally_supplied_proportion_renormalized"
                if renormalized
                else "externally_supplied_proportion"
            )
        weights.append(
            TranscriptPriorWeightRecordV1(
                record_id=stable_id("tx-weight", gene_record_id, transcript_id, weight_type),
                gene_isoform_uncertainty_record_id=gene_record_id,
                original_gene_id=original_gene_id,
                canonical_gene_id=canonical_gene_id,
                original_transcript_id=record.original_transcript_id,
                canonical_transcript_id=transcript_id,
                transcript_version=record.transcript_version,
                transcript_biotype=record.transcript_biotype,
                annotation_status="annotation_eligible",
                eligibility_status="eligible",
                exclusion_reason=None,
                weight=weight,
                weight_type=weight_type,
                weight_source="precomputed_transcript_proportions",
                weight_evidence_status=evidence_status,
                source_method=external.source_method if external else None,
                source_software=external.source_software if external else None,
                source_software_version=external.source_software_version if external else None,
                source_annotation_release=record.annotation_release,
                warnings=("external proportions renormalized by explicit policy",)
                if renormalized and external
                else (),
                provenance_record_ids=(external.source_file_checksum,) if external else (),
            )
        )
    total = sum(item.weight or 0.0 for item in weights)
    if not math.isclose(total, 1.0, abs_tol=tolerance):
        raise ValueError("external proportions do not sum to 1 within tolerance")
    return weights, total


def assign_isoform_uncertainty_for_gene(
    *,
    source_expression_v2_record_id: str,
    original_gene_id: str,
    canonical_gene_id: str,
    approved_symbol: str | None,
    organism: str,
    assembly: str,
    annotation_snapshot: TranscriptAnnotationSnapshotV1,
    annotation_records: list[TranscriptAnnotationRecordV1],
    policy: TranscriptSetPolicyV1,
    external_proportions: list[ExternalTranscriptProportionRecordV1] | None = None,
    external_policy: ExternalTranscriptProportionPolicyV1 | None = None,
    tolerance: float = 1e-6,
) -> tuple[
    GeneIsoformUncertaintyRecordV1,
    list[TranscriptPriorWeightRecordV1],
    list[TranscriptSetExclusionRecordV1],
]:
    external_policy = external_policy or ExternalTranscriptProportionPolicyV1()
    eligible, exclusions = _eligible_and_excluded(
        canonical_gene_id, annotation_records, annotation_snapshot, policy
    )
    gene_record_id = stable_id(
        "gene-isoform-uncertainty",
        source_expression_v2_record_id,
        canonical_gene_id,
        annotation_snapshot.fingerprint,
        policy.fingerprint,
        external_proportions or "equal_prior",
    )
    if not eligible:
        weights: list[TranscriptPriorWeightRecordV1] = []
        weight_sum = 0.0
        mode: IsoformEvidenceMode = "annotation_only_equal_prior"
        status: IsoformResolutionStatus = "no_eligible_transcripts"
        prior_method = "none_no_eligible_transcripts"
        warnings: tuple[str, ...] = ("no eligible transcripts; no prior weights generated",)
    elif external_proportions:
        valid, errors, _total = validate_external_proportions(
            proportions=external_proportions,
            eligible_transcripts=eligible,
            snapshot=annotation_snapshot,
            tolerance=tolerance,
            policy=external_policy,
        )
        used_equal_prior_fallback = False
        if (
            not valid
            and "missing_transcript_proportion" in errors
            and external_policy.missing_transcript_behavior == "fallback_to_equal_prior"
        ):
            weights, weight_sum = build_equal_prior_weights(
                gene_record_id=gene_record_id,
                original_gene_id=original_gene_id,
                canonical_gene_id=canonical_gene_id,
                eligible_transcripts=eligible,
                tolerance=tolerance,
            )
            mode = "annotation_only_equal_prior"
            status = (
                "single_eligible_transcript"
                if len(eligible) == 1
                else "multiple_transcripts_equal_prior"
            )
            prior_method = "equal_weight_per_eligible_transcript_after_missing_external"
            warnings = tuple(errors)
            errors = ()
            valid = True
            used_equal_prior_fallback = True
        if not valid and external_policy.invalid_proportion_behavior == "fail_stage":
            raise IsoformUncertaintyPolicyError(
                f"external transcript proportions failed policy for {canonical_gene_id}: "
                f"{', '.join(errors)}"
            )
        if used_equal_prior_fallback:
            pass
        elif not valid:
            if external_policy.invalid_proportion_behavior == "preserve_invalid_with_status":
                weights = [
                    TranscriptPriorWeightRecordV1(
                        record_id=stable_id(
                            "tx-weight", gene_record_id, record.original_transcript_id, "invalid"
                        ),
                        gene_isoform_uncertainty_record_id=gene_record_id,
                        original_gene_id=original_gene_id,
                        canonical_gene_id=canonical_gene_id,
                        original_transcript_id=record.original_transcript_id,
                        canonical_transcript_id=record.canonical_transcript_id
                        or record.original_transcript_id,
                        transcript_version=record.transcript_version,
                        transcript_biotype=record.transcript_biotype,
                        annotation_status="annotation_eligible",
                        eligibility_status="eligible",
                        exclusion_reason=None,
                        weight=None,
                        weight_type="unavailable",
                        weight_source="precomputed_transcript_proportions",
                        weight_evidence_status="external_proportions_invalid_preserved_with_status",
                        source_annotation_release=record.annotation_release,
                        warnings=errors,
                    )
                    for record in sorted(eligible, key=lambda item: item.original_transcript_id)
                ]
            else:
                weights = []
            weight_sum = 0.0
            mode = "precomputed_transcript_proportions"
            status = "invalid_external_proportions"
            prior_method = "external_proportions_rejected"
            warnings = errors
        else:
            weights, weight_sum = _external_weight_records(
                gene_record_id=gene_record_id,
                original_gene_id=original_gene_id,
                canonical_gene_id=canonical_gene_id,
                eligible_transcripts=eligible,
                proportions=external_proportions,
                tolerance=tolerance,
                external_policy=external_policy,
            )
            mode = "precomputed_transcript_proportions"
            status = (
                "single_eligible_transcript"
                if len(eligible) == 1
                else "multiple_transcripts_external_proportions"
            )
            prior_method = "validated_external_transcript_proportions"
            warnings = ()
    else:
        weights, weight_sum = build_equal_prior_weights(
            gene_record_id=gene_record_id,
            original_gene_id=original_gene_id,
            canonical_gene_id=canonical_gene_id,
            eligible_transcripts=eligible,
            tolerance=tolerance,
        )
        mode = "annotation_only_equal_prior"
        status = (
            "single_eligible_transcript"
            if len(eligible) == 1
            else "multiple_transcripts_equal_prior"
        )
        prior_method = "equal_weight_per_eligible_transcript"
        if len(eligible) == 1:
            warnings = ()
        else:
            warnings = ("transcript-specific abundance unresolved; equal prior applied",)
    gene_record = GeneIsoformUncertaintyRecordV1(
        record_id=gene_record_id,
        source_expression_v2_record_id=source_expression_v2_record_id,
        original_gene_id=original_gene_id,
        canonical_gene_id=canonical_gene_id,
        approved_symbol=approved_symbol,
        organism=organism,
        assembly=assembly,
        annotation_snapshot_id=annotation_snapshot.snapshot_id,
        annotation_checksum=annotation_snapshot.source_file_checksum,
        transcript_set_policy_id=policy.policy_id,
        annotated_transcript_count=len(
            [
                record
                for record in annotation_records
                if record.canonical_gene_id == canonical_gene_id
                or record.original_gene_id == canonical_gene_id
            ]
        ),
        eligible_transcript_count=len(eligible),
        excluded_transcript_count=len(exclusions),
        isoform_evidence_mode=mode,
        isoform_resolution_status=status,
        prior_method=prior_method,
        weight_sum=weight_sum,
        transcript_weight_record_ids=tuple(item.record_id for item in weights),
        input_proportion_source=(
            external_proportions[0].source_file_checksum if external_proportions else None
        ),
        warnings=tuple(warnings),
        exclusion_reasons=tuple(record.exclusion_reason for record in exclusions),
        provenance_record_ids=(source_expression_v2_record_id, annotation_snapshot.snapshot_id),
    )
    return gene_record, weights, exclusions
