from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


CalibrationStatus = Literal[
    "definitive",
    "definitive_zero_no_decrease",
    "unavailable_missing_expression",
    "unavailable_invalid_intended_target",
    "unavailable_intended_target_ratio",
    "unavailable_not_decreased",
    "unavailable_inconsistent_calibration",
]

ExpectedDirectEffectStatus = Literal[
    "definitive",
    "unavailable_missing_expression",
    "unavailable_ratio",
    "unavailable_calibration",
]


class ExpectedDirectEffectPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "expected-direct-effect-v1-equal-transcript-prior"
    expression_source_contract: Literal["ExpressionAnalysisResultV2"] = "ExpressionAnalysisResultV2"
    ratio_source_contract: Literal["TranscriptTargetabilityRatioResultV1"] = (
        "TranscriptTargetabilityRatioResultV1"
    )
    normalized_expression_artifact: Literal["normalized_gene_effects_v2.jsonl"] = (
        "normalized_gene_effects_v2.jsonl"
    )
    targetability_ratio_artifact: Literal["gene_transcript_targetability_ratios_v1.jsonl"] = (
        "gene_transcript_targetability_ratios_v1.jsonl"
    )
    calibration_model: Literal[
        "gene_observed_remaining_fraction_divided_by_targetable_fraction"
    ] = "gene_observed_remaining_fraction_divided_by_targetable_fraction"
    residual_interpretation: Literal["unresolved_residual_only"] = "unresolved_residual_only"
    pathway_evidence_used: bool = False
    classification_performed: bool = False
    include_seed_only_as_targetable: bool = False
    missing_sequence_behavior: Literal["preserve_unresolved_ratio"] = "preserve_unresolved_ratio"
    numerical_tolerance: float = 1e-9
    warning_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_guardrails(self) -> ExpectedDirectEffectPolicyV1:
        if self.pathway_evidence_used:
            raise ValueError("pathway evidence is not part of expected direct-effect estimation")
        if self.classification_performed:
            raise ValueError("classification is not part of expected direct-effect estimation")
        if self.include_seed_only_as_targetable:
            raise ValueError("seed-only evidence must remain excluded from formal M")
        if self.numerical_tolerance <= 0:
            raise ValueError("numerical_tolerance must be positive")
        return self

    @property
    def fingerprint(self) -> str:
        return stable_id("expected-direct-effect-policy", self.model_dump(mode="json"))


class IntendedTargetKnockdownCalibrationRecordV1(BaseModel):
    schema_version: str = "1"
    calibration_record_id: str
    intended_target_gene_id: str
    intended_target_expression_record_id: str | None
    intended_target_ratio_record_id: str | None
    intended_target_normalized_log2fc: float | None
    intended_target_N: int | None
    intended_target_M: int | None
    intended_targetable_fraction: float | None
    intended_observed_remaining_fraction: float | None
    raw_calibration_knockdown_fraction: float | None
    accepted_calibration_knockdown_fraction: float | None
    numerical_tolerance: float
    status: CalibrationStatus
    warning_codes: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()
    source_expression_checksum: str | None = None
    source_ratio_checksum: str | None = None


class GeneExpectedDirectEffectRecordV1(BaseModel):
    schema_version: str = "1"
    expected_direct_effect_record_id: str
    canonical_gene_id: str
    approved_symbol: str | None = None
    source_expression_record_id: str | None
    source_ratio_record_id: str | None
    source_calibration_record_id: str
    observed_normalized_log2fc: float | None
    n_total_eligible_transcripts: int | None
    m_targetable_transcripts: int | None
    targetable_fraction_m_over_n: float | None
    ratio_status: str | None
    intended_target_calibration_value: float | None
    expected_remaining_fraction: float | None
    expected_direct_effect_log2fc: float | None
    observed_vs_expected_log2_difference: float | None
    unresolved_residual_log2fc: float | None
    status: ExpectedDirectEffectStatus
    unresolved_reason: str | None = None
    evidence_fields_kept_separate: bool = True
    residual_interpretation: Literal["unresolved_residual_only"] = "unresolved_residual_only"
    warning_codes: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_residual_guardrail(self) -> GeneExpectedDirectEffectRecordV1:
        if self.residual_interpretation != "unresolved_residual_only":
            raise ValueError("residual must remain unresolved in this stage")
        return self


class UnresolvedExpectedDirectEffectRecordV1(BaseModel):
    schema_version: str = "1"
    unresolved_record_id: str
    canonical_gene_id: str
    reason: str
    source_expression_record_id: str | None = None
    source_ratio_record_id: str | None = None
    source_calibration_record_id: str | None = None
    preserved_upstream_status: str | None = None
    warnings: tuple[str, ...] = ()


class ExpectedDirectEffectRunRecordV1(BaseModel):
    schema_version: str = "1"
    run_id: str
    stage_name: Literal["expected_direct_effect"] = "expected_direct_effect"
    expression_result_id: str
    expression_checksum: str
    transcript_targetability_ratio_result_id: str
    transcript_targetability_ratio_checksum: str
    policy_id: str
    policy_checksum: str
    calibration_record_id: str
    calibration_checksum: str | None = None
    started_at: str
    completed_at: str
    status: Literal["completed", "failed"]
    source_counts: dict[str, int] = Field(default_factory=dict)
    output_counts: dict[str, int] = Field(default_factory=dict)
    output_checksums: dict[str, str] = Field(default_factory=dict)
    verification_status: Literal["verified", "failed"]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class ExpectedDirectEffectVerificationRecordV1(BaseModel):
    schema_version: str = "1"
    verification_id: str
    calibration_checks: Literal["passed", "failed"]
    expression_checks: Literal["passed", "failed"]
    ratio_checks: Literal["passed", "failed"]
    arithmetic_checks: Literal["passed", "failed"]
    residual_guardrail_checks: Literal["passed", "failed"]
    artifact_reference_checks: Literal["passed", "failed"]
    count_reconciliation_checks: Literal["passed", "failed"]
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    verified_at: str


class ExpectedDirectEffectResultV1(BaseModel):
    schema_version: str = "1"
    run_record: ExpectedDirectEffectRunRecordV1
    policy_artifact: str
    calibration_artifact: str
    gene_effect_records_artifact: str
    unresolved_records_artifact: str
    summary_artifact: str
    verification_artifact: str
    warnings_artifact: str
    canonical_artifact_checksums: dict[str, str]
    counts: dict[str, int]
    status: Literal["completed", "failed"]
    warnings: tuple[str, ...] = ()
