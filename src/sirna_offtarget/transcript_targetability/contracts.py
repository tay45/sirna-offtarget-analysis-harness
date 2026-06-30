from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

EvidenceClass = Literal[
    "exact_full_length_complement",
    "near_full_length_complement",
    "cleavage_compatible_candidate",
    "seed_only_candidate",
    "partial_nonseed_match",
    "ambiguous_alignment",
    "no_supported_site",
    "transcript_sequence_unavailable",
    "unsupported_alignment",
    "invalid_input",
    "not_evaluated_due_to_gene_failure",
]
TargetabilityDecisionStatus = Literal[
    "cleavage_candidate_present",
    "seed_only_candidate_present",
    "no_supported_site",
    "indeterminate",
    "sequence_unavailable",
    "gene_failed_missing_transcript_sequence",
    "not_evaluated_due_to_gene_failure",
]


def stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


class SiRNASequenceRecordV1(BaseModel):
    schema_version: str = "1"
    sirna_id: str
    reagent_name: str
    guide_sequence_original: str
    guide_sequence_normalized: str
    guide_length: int
    guide_alphabet: Literal["RNA", "DNA", "CANONICAL_DNA"]
    guide_orientation: Literal["guide_5p_to_3p"]
    guide_strand_status: Literal["explicit", "unknown", "ambiguous"] = "explicit"
    passenger_sequence_original: str | None = None
    passenger_sequence_normalized: str | None = None
    passenger_sequence_status: Literal["not_supplied", "explicit", "unknown"] = "not_supplied"
    intended_target_gene_id: str | None = None
    intended_target_transcript_ids: tuple[str, ...] = ()
    organism: str
    assembly: str
    sequence_source: str
    source_file: str | None = None
    source_file_checksum: str | None = None
    chemical_modification_status: Literal["none_declared", "declared_not_modeled"] = "none_declared"
    warnings: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_explicit_guide(self) -> SiRNASequenceRecordV1:
        if self.guide_strand_status != "explicit":
            raise ValueError("guide strand must be explicit for production targetability")
        if self.guide_length != len(self.guide_sequence_normalized):
            raise ValueError("guide_length must match normalized guide sequence")
        return self


class SiRNASequenceValidationRecordV1(BaseModel):
    schema_version: str = "1"
    validation_id: str
    sirna_id: str
    guide_valid: bool
    guide_length: int | None = None
    guide_length_min: int | None = None
    guide_length_max: int | None = None
    guide_length_status: Literal["valid", "too_short", "too_long"] | None = None
    guide_reverse_complement: str
    passenger_valid: bool | None = None
    passenger_search_status: Literal["unsupported", "not_requested"] = "not_requested"
    fatal_errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class IntendedTargetValidationPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "intended-target-validation-v1-actual-site"
    intended_target_required: bool = True
    transcript_ids_required: bool = False
    accepted_evidence_classes: tuple[EvidenceClass, ...] = (
        "exact_full_length_complement",
        "near_full_length_complement",
    )
    maximum_total_mismatches: int = 2
    maximum_seed_mismatches: int = 0
    maximum_central_mismatches: int = 0
    failure_behavior: Literal["fail_stage", "warning", "preserve_invalid_with_status"] = (
        "fail_stage"
    )
    gene_only_behavior: Literal[
        "warning",
        "fail_stage",
        "preserve_uncertainty",
        "accept_any_gene_transcript_site",
    ] = "preserve_uncertainty"
    warnings: tuple[str, ...] = ()

    @property
    def fingerprint(self) -> str:
        return stable_id("intended-target-policy", self.model_dump(exclude={"policy_id"}))


class MissingTranscriptSequencePolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "missing-transcript-sequence-v1-record-unavailable"
    mode: Literal["fail_stage", "record_unavailable_and_continue", "fail_gene"] = (
        "record_unavailable_and_continue"
    )
    warnings: tuple[str, ...] = ()

    @property
    def fingerprint(self) -> str:
        return stable_id("missing-sequence-policy", self.model_dump(exclude={"policy_id"}))


class TranscriptSequenceSnapshotV1(BaseModel):
    schema_version: str = "1"
    snapshot_id: str
    provider: str
    release: str
    organism: str
    assembly: str
    transcript_identifier_namespace: str
    sequence_alphabet: Literal["DNA", "RNA"] = "DNA"
    transcript_count: int
    sequence_file_checksum: str
    manifest_checksum: str | None = None
    verification_status: Literal["verified", "unverified"]
    generation_method: str


class TranscriptSequenceRecordV1(BaseModel):
    schema_version: str = "1"
    canonical_gene_id: str
    canonical_transcript_id: str
    transcript_version: str | None = None
    sequence: str
    sequence_checksum: str | None = None

    @field_validator("sequence")
    @classmethod
    def validate_sequence(cls, value: str) -> str:
        normalized = value.upper().replace("U", "T")
        if not normalized:
            raise ValueError("transcript sequence must not be empty")
        if set(normalized) - set("ACGT"):
            raise ValueError("transcript sequence contains unsupported bases")
        return normalized


class TranscriptSequenceSnapshotValidationRecordV1(BaseModel):
    schema_version: str = "1"
    validation_id: str
    snapshot_id: str
    provider_release_match: bool
    organism_match: bool
    assembly_match: bool
    transcript_namespace_match: bool
    duplicate_sequence_ids: tuple[str, ...] = ()
    missing_eligible_transcripts: tuple[str, ...] = ()
    wrong_gene_assignments: tuple[str, ...] = ()
    invalid_sequence_ids: tuple[str, ...] = ()
    sequence_count: int
    verification_status: Literal["verified", "failed"]
    warnings: tuple[str, ...] = ()
    fatal_errors: tuple[str, ...] = ()


class CleavageCompatibilityPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "cleavage-compatibility-v1-conservative-ungapped"
    guide_length_min: int = 19
    guide_length_max: int = 23
    maximum_total_mismatches: int = 2
    maximum_seed_mismatches: int = 0
    maximum_central_mismatches: int = 0
    maximum_nonseed_mismatches: int = 2
    allowed_indels: bool = False
    allowed_bulges: bool = False
    seed_start: int = 2
    seed_end: int = 8
    central_region_start: int = 9
    central_region_end: int = 12
    supplementary_region: tuple[int, int] = (13, 19)
    terminal_overhang_handling: str = "ignored_not_searched"
    exact_match_precedence: bool = True
    alignment_scoring_method: str = "ungapped_substitution_count"
    deterministic_tie_breaking: str = "evidence_priority_mismatches_coordinate"
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_policy(self) -> CleavageCompatibilityPolicyV1:
        if self.allowed_indels or self.allowed_bulges:
            raise ValueError("initial production targetability supports ungapped matching only")
        for value in (
            self.maximum_total_mismatches,
            self.maximum_seed_mismatches,
            self.maximum_central_mismatches,
            self.maximum_nonseed_mismatches,
        ):
            if value < 0:
                raise ValueError("mismatch limits must be non-negative")
        if self.seed_start < 1 or self.seed_end < self.seed_start:
            raise ValueError("invalid seed coordinates")
        if self.central_region_start < 1 or self.central_region_end < self.central_region_start:
            raise ValueError("invalid central coordinates")
        return self

    @property
    def fingerprint(self) -> str:
        return stable_id("cleavage-policy", self.model_dump(exclude={"policy_id"}))


class SeedMatchPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "seed-match-v1-exact-seed-separate"
    seed_start: int = 2
    seed_end: int = 8
    seed_length: int = 7
    exact_seed_required: bool = True
    allowed_seed_mismatches: int = 0
    supplementary_pairing_requirement: str = "record_only"
    minimum_total_paired_bases: int = 7
    maximum_total_mismatches: int = 14
    allowed_bulges: bool = False
    allowed_indels: bool = False
    transcript_region_restrictions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_policy(self) -> SeedMatchPolicyV1:
        if self.seed_start < 1 or self.seed_end < self.seed_start:
            raise ValueError("invalid seed coordinates")
        if self.seed_length != self.seed_end - self.seed_start + 1:
            raise ValueError("seed_length must match seed coordinates")
        if self.exact_seed_required and self.allowed_seed_mismatches > 0:
            raise ValueError("exact_seed_required conflicts with allowed_seed_mismatches")
        if self.minimum_total_paired_bases < self.seed_length:
            raise ValueError("minimum_total_paired_bases must be at least seed_length")
        if self.allowed_seed_mismatches < 0 or self.maximum_total_mismatches < 0:
            raise ValueError("mismatch limits must be non-negative")
        if self.allowed_bulges or self.allowed_indels:
            raise ValueError("initial seed search supports ungapped matching only")
        if self.supplementary_pairing_requirement not in {"record_only", "not_required"}:
            raise ValueError("unsupported_supplementary_pairing_policy")
        if self.transcript_region_restrictions:
            raise ValueError("unsupported_transcript_region_restrictions")
        return self

    @property
    def fingerprint(self) -> str:
        return stable_id("seed-policy", self.model_dump(exclude={"policy_id"}))


class TranscriptTargetabilityMismatchRecordV1(BaseModel):
    schema_version: str = "1"
    mismatch_record_id: str
    site_record_id: str
    guide_position: int
    target_position: int
    guide_base: str
    target_paired_base: str
    match_status: Literal["mismatch"] = "mismatch"
    mismatch_region: Literal["seed", "central", "nonseed", "terminal"]
    mismatch_type: str
    seed_membership: bool
    central_region_membership: bool
    terminal_region_membership: bool


class TranscriptTargetabilityAlignmentPositionRecordV1(BaseModel):
    schema_version: str = "1"
    position_record_id: str
    site_record_id: str
    guide_position: int
    transcript_position: int
    guide_base: str
    target_base: str
    pairing_status: Literal["match", "mismatch"]
    seed_membership: bool
    central_membership: bool
    terminal_membership: bool
    warnings: tuple[str, ...] = ()


class TranscriptTargetabilitySiteRecordV1(BaseModel):
    schema_version: str = "1"
    site_record_id: str
    sirna_id: str
    source_isoform_uncertainty_record_id: str
    source_transcript_weight_record_id: str
    canonical_gene_id: str
    canonical_transcript_id: str
    transcript_version: str | None = None
    transcript_sequence_snapshot_id: str
    transcript_sequence_checksum: str
    guide_sequence_record_id: str
    guide_search_sequence: str
    transcript_site_sequence: str
    alignment_orientation: Literal["guide_reverse_complement_to_transcript_5p_to_3p"]
    transcript_start: int
    transcript_end: int
    coordinate_system: str = "transcript_zero_based_half_open"
    alignment_length: int
    matched_base_count: int
    minimum_total_paired_bases: int = 0
    paired_base_policy_status: Literal["passed", "failed", "not_applicable"] = "not_applicable"
    total_mismatch_count: int
    seed_mismatch_count: int
    central_mismatch_count: int
    nonseed_mismatch_count: int
    mismatch_positions: tuple[int, ...] = ()
    gap_count: int = 0
    bulge_status: Literal["not_searched_ungapped"] = "not_searched_ungapped"
    seed_match_status: Literal["exact_seed", "seed_mismatch", "not_applicable"]
    supplementary_pairing_status: str
    evidence_class: EvidenceClass
    cleavage_compatibility_status: Literal[
        "cleavage_compatible_candidate", "not_cleavage_compatible"
    ]
    seed_only_status: Literal["seed_only_candidate", "not_seed_only"]
    transcript_region: str = "unknown"
    alignment_score: int
    ranking_tuple: tuple[int, int, int, int, int]
    warnings: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()


class TranscriptTargetabilityEvidenceRecordV1(BaseModel):
    schema_version: str = "1"
    evidence_record_id: str
    sirna_id: str
    canonical_gene_id: str
    canonical_transcript_id: str
    transcript_version: str | None = None
    source_isoform_uncertainty_record_id: str
    source_transcript_weight_record_id: str
    transcript_prior_weight: float | None
    sequence_available: bool
    sites_examined: int
    qualifying_site_count: int
    exact_site_count: int
    near_full_length_site_count: int
    cleavage_candidate_site_count: int
    seed_only_site_count: int
    partial_match_site_count: int
    best_site_record_id: str | None = None
    site_record_ids: tuple[str, ...] = ()
    evidence_status: TargetabilityDecisionStatus
    targetability_decision_status: TargetabilityDecisionStatus
    targetability_decision_reason: str
    tie_status: Literal["none", "tied_best_sites"] = "none"
    warnings: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()


class TranscriptTargetabilityGeneFailureRecordV1(BaseModel):
    schema_version: str = "1"
    failure_record_id: str
    canonical_gene_id: str
    affected_transcript_ids: tuple[str, ...]
    triggering_transcript_ids: tuple[str, ...]
    failure_reason: str
    missing_sequence_policy_id: str
    source_isoform_uncertainty_record_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()


class IntendedTargetValidationRecordV1(BaseModel):
    schema_version: str = "1"
    validation_record_id: str
    policy_id: str
    intended_target_required: bool
    transcript_ids_required: bool
    intended_target_gene_id: str | None = None
    intended_target_transcript_ids: tuple[str, ...] = ()
    supplied_input_status: Literal[
        "not_requested",
        "missing_required",
        "gene_only",
        "transcript_ids_supplied",
    ]
    gene_only_behavior: str
    candidate_site_ids: tuple[str, ...] = ()
    accepted_site_ids: tuple[str, ...] = ()
    rejected_site_ids: tuple[str, ...] = ()
    rejection_reasons: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    best_accepted_site_id: str | None = None
    mismatch_threshold_checks: dict[str, str] = Field(default_factory=dict)
    evidence_class_checks: dict[str, str] = Field(default_factory=dict)
    sequence_availability_checks: dict[str, str] = Field(default_factory=dict)
    gene_failure_checks: dict[str, str] = Field(default_factory=dict)
    validation_status: Literal[
        "passed",
        "failed",
        "warning",
        "invalid_preserved",
        "uncertain",
        "not_requested",
    ]
    failure_behavior_applied: Literal[
        "none",
        "fail_stage",
        "warning",
        "preserve_invalid_with_status",
    ] = "none"
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()


class TranscriptTargetabilityRunRecordV1(BaseModel):
    schema_version: str = "1"
    run_id: str
    stage_name: str = "transcript_targetability"
    sirna_sequence_record_id: str
    guide_sequence_checksum: str
    isoform_uncertainty_result_id: str
    isoform_uncertainty_artifact_checksum: str
    transcript_sequence_snapshot_id: str
    transcript_sequence_snapshot_checksum: str
    annotation_snapshot_id: str
    annotation_checksum: str
    cleavage_policy_id: str
    seed_policy_id: str
    intended_target_policy_id: str = "not_applicable"
    missing_sequence_policy_id: str = "not_applicable"
    passenger_search_status: Literal["unsupported", "not_requested"] = "not_requested"
    alignment_policy_id: str = "ungapped-substitution-v1"
    organism: str
    assembly: str
    started_at: str
    completed_at: str
    status: Literal["completed", "failed"]
    source_counts: dict[str, int] = Field(default_factory=dict)
    output_counts: dict[str, int] = Field(default_factory=dict)
    output_checksums: dict[str, str] = Field(default_factory=dict)
    verification_status: Literal["verified", "failed"]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class TranscriptTargetabilityResultV1(BaseModel):
    schema_version: str = "1"
    run_record: TranscriptTargetabilityRunRecordV1
    sirna_sequence_validation_artifact: str
    transcript_sequence_snapshot_validation_artifact: str
    targetability_evidence_artifact: str
    targetability_sites_artifact: str
    mismatch_detail_artifact: str
    alignment_positions_artifact: str | None = None
    transcript_sequence_snapshot_artifact: str | None = None
    transcript_sequence_records_artifact: str | None = None
    gene_failures_artifact: str | None = None
    intended_target_validation_artifact: str | None = None
    exclusions_artifact: str
    summary_artifact: str
    warnings_artifact: str
    output_checksums: dict[str, str]
    counts: dict[str, int]
    status: Literal["completed", "failed"]


class TranscriptTargetabilityVerificationRecordV1(BaseModel):
    schema_version: str = "1"
    verification_id: str
    verifier_schema_version: str = "transcript-targetability-independent-verifier-v2"
    transcript_snapshot_reload_check: str = "not_checked"
    transcript_lookup_checks: str = "not_checked"
    transcript_checksum_checks: str = "not_checked"
    transcript_slice_checks: str = "not_checked"
    guide_sequence_check: str
    guide_length_check: str
    orientation_check: str
    transcript_sequence_checks: str
    site_coordinate_checks: str
    site_sequence_checks: str
    guide_search_sequence_checks: str = "not_checked"
    alignment_recomputation_checks: str = "not_checked"
    mismatch_detail_checks: str
    mismatch_recomputation_checks: str = "not_checked"
    mismatch_region_checks: str = "not_checked"
    seed_count_checks: str
    central_count_checks: str
    paired_base_checks: str = "not_checked"
    evidence_class_checks: str
    site_id_checks: str = "not_checked"
    ranking_checks: str
    evidence_aggregation_checks: str = "not_checked"
    gene_failure_checks: str = "not_checked"
    intended_target_policy_checks: str = "not_checked"
    intended_target_checks: str
    reference_checks: str
    artifact_checksum_checks: str
    count_checks: str
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    verified_at: str
