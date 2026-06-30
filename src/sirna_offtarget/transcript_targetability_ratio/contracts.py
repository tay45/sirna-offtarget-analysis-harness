from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


TargetabilityRatioStatus = Literal[
    "definitive",
    "unavailable_incomplete_evidence",
    "unavailable_gene_failure",
    "undefined_zero_denominator",
]
MStatus = Literal[
    "definitive",
    "unavailable_incomplete_evidence",
    "unavailable_gene_failure",
    "undefined_zero_denominator",
]


class TargetableTranscriptInclusionPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "targetable-transcript-inclusion-v1-cleavage-compatible"
    policy_name: str = "Default verified cleavage-compatible transcript inclusion"
    strand_role: Literal["guide"] = "guide"
    included_evidence_classes: tuple[str, ...] = (
        "exact_full_length_complement",
        "near_full_length_complement",
        "cleavage_compatible_candidate",
    )
    require_cleavage_compatibility: bool = True
    include_exact_full_length: bool = True
    include_near_full_length: bool = True
    include_seed_only: bool = False
    include_ambiguous: bool = False
    require_verified_sequence: bool = True
    require_verified_site: bool = True
    require_complete_gene_evidence: bool = True
    unavailable_sequence_behavior: Literal["ratio_unavailable"] = "ratio_unavailable"
    failed_gene_behavior: Literal["ratio_unavailable"] = "ratio_unavailable"
    multiple_site_counting_rule: Literal["count_transcript_once"] = "count_transcript_once"
    transcript_counting_rule: Literal["unique_canonical_transcript"] = "unique_canonical_transcript"
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_supported_policy(self) -> TargetableTranscriptInclusionPolicyV1:
        if self.strand_role != "guide":
            raise ValueError("only guide strand inclusion is supported")
        if self.include_seed_only:
            raise ValueError("seed-only inclusion is unsupported for the official ratio")
        if self.include_ambiguous:
            raise ValueError("ambiguous evidence inclusion is unsupported")
        if not self.require_cleavage_compatibility:
            raise ValueError("formal M requires cleavage-compatible evidence")
        if not self.require_verified_sequence or not self.require_verified_site:
            raise ValueError("formal M requires verified sequence and site evidence")
        if not self.require_complete_gene_evidence:
            raise ValueError("official M/N requires complete gene targetability evidence")
        if self.multiple_site_counting_rule != "count_transcript_once":
            raise ValueError("multiple sites must count a transcript once")
        if self.transcript_counting_rule != "unique_canonical_transcript":
            raise ValueError("transcripts must be counted by unique canonical transcript id")
        return self

    @property
    def fingerprint(self) -> str:
        return stable_id("targetable-transcript-inclusion-policy", self.model_dump(mode="json"))


class TranscriptMContributionRecordV1(BaseModel):
    schema_version: str = "1"
    contribution_record_id: str
    canonical_gene_id: str
    canonical_transcript_id: str
    transcript_version: str | None = None
    source_transcript_weight_record_id: str
    source_targetability_evidence_record_id: str | None = None
    eligible_for_n: bool
    evaluable_for_m: bool
    qualifying_for_m: bool
    contribution_to_n: int
    contribution_to_m: int | None
    qualifying_evidence_class: str | None = None
    qualifying_site_ids: tuple[str, ...] = ()
    seed_only_evidence_present: bool = False
    exclusion_or_unavailability_reason: str | None = None
    transcript_prior_weight: float | None = None
    warnings: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()


class GeneTranscriptTargetabilityRatioRecordV1(BaseModel):
    schema_version: str = "1"
    ratio_record_id: str
    canonical_gene_id: str
    source_isoform_uncertainty_record_id: str
    source_targetability_result_id: str
    targetability_inclusion_policy_id: str
    eligible_transcript_ids: tuple[str, ...]
    n_total_eligible_transcripts: int
    evaluable_transcript_ids: tuple[str, ...]
    n_evaluable_transcripts: int
    unresolved_transcript_ids: tuple[str, ...]
    unresolved_transcript_count: int
    qualifying_transcript_ids: tuple[str, ...]
    observed_qualifying_transcript_count: int
    m_targetable_transcripts: int | None
    m_status: MStatus
    ratio_m_over_n: float | None
    ratio_status: TargetabilityRatioStatus
    ratio_unavailable_reason: str | None = None
    equal_prior_weight_per_transcript: float | None
    qualifying_equal_prior_weight_sum: float | None
    equal_prior_consistency_status: Literal["passed", "not_applicable", "failed"]
    seed_only_transcript_ids: tuple[str, ...] = ()
    seed_only_transcript_count: int = 0
    nonqualifying_transcript_ids: tuple[str, ...] = ()
    gene_failure_record_id: str | None = None
    optional_m_lower_bound: int | None = None
    optional_m_upper_bound: int | None = None
    optional_ratio_lower_bound: float | None = None
    optional_ratio_upper_bound: float | None = None
    warnings: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()


class UnresolvedTargetabilityRatioEvidenceRecordV1(BaseModel):
    schema_version: str = "1"
    unresolved_record_id: str
    canonical_gene_id: str
    canonical_transcript_id: str
    reason: str
    source_record_id: str | None = None
    warnings: tuple[str, ...] = ()


class TranscriptTargetabilityRatioRunRecordV1(BaseModel):
    schema_version: str = "1"
    run_id: str
    stage_name: Literal["transcript_targetability_ratio"] = "transcript_targetability_ratio"
    isoform_uncertainty_result_id: str
    isoform_uncertainty_checksum: str
    transcript_targetability_result_id: str
    transcript_targetability_checksum: str
    inclusion_policy_id: str
    inclusion_policy_checksum: str
    started_at: str
    completed_at: str
    status: Literal["completed", "failed"]
    source_counts: dict[str, int] = Field(default_factory=dict)
    output_counts: dict[str, int] = Field(default_factory=dict)
    output_checksums: dict[str, str] = Field(default_factory=dict)
    verification_status: Literal["verified", "failed"]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class TranscriptTargetabilityRatioVerificationRecordV1(BaseModel):
    schema_version: str = "1"
    verification_id: str
    transcript_set_checks: Literal["passed", "failed"]
    n_count_checks: Literal["passed", "failed"]
    m_count_checks: Literal["passed", "failed"]
    unique_transcript_checks: Literal["passed", "failed"]
    inclusion_policy_checks: Literal["passed", "failed"]
    seed_only_exclusion_checks: Literal["passed", "failed"]
    unavailable_evidence_checks: Literal["passed", "failed"]
    failed_gene_checks: Literal["passed", "failed"]
    zero_denominator_checks: Literal["passed", "failed"]
    equal_prior_weight_checks: Literal["passed", "failed"]
    ratio_arithmetic_checks: Literal["passed", "failed"]
    artifact_reference_checks: Literal["passed", "failed"]
    count_reconciliation_checks: Literal["passed", "failed"]
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    verified_at: str


class TranscriptTargetabilityRatioResultV1(BaseModel):
    schema_version: str = "1"
    run_record: TranscriptTargetabilityRatioRunRecordV1
    inclusion_policy_artifact: str
    gene_ratio_records_artifact: str
    transcript_contribution_records_artifact: str
    unresolved_evidence_records_artifact: str
    summary_artifact: str
    verification_artifact: str
    warnings_artifact: str
    canonical_artifact_checksums: dict[str, str]
    counts: dict[str, int]
    status: Literal["completed", "failed"]
    warnings: tuple[str, ...] = ()
