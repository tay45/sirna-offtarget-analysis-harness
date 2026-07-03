from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


ResidualDirection = Literal[
    "more_decreased_than_expected",
    "less_decreased_or_increased_than_expected",
    "matches_expected_direct_effect",
]

ResidualMagnitudeStatus = Literal[
    "negligible_residual",
    "weak_residual",
    "moderate_residual",
    "strong_residual",
]

ResidualSupportStatus = Literal[
    "no_residual_to_attribute",
    "residual_without_pathway_support",
    "residual_with_weak_pathway_support",
    "residual_with_moderate_pathway_support",
    "residual_with_strong_pathway_support",
    "unresolved_missing_pathway_evidence",
    "unresolved_upstream_expected_effect",
]


INTERPRETATION_BOUNDARY = (
    "residual_support_characterization_only; pathway support is supporting context; "
    "direct_secondary_mixed_calling_remains_planned"
)


class ResidualAttributionPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "residual-attribution-v1-support-characterization"
    numerical_tolerance: float = 1e-9
    negligible_residual_abs_log2_threshold: float = 0.10
    moderate_residual_abs_log2_threshold: float = 0.50
    strong_residual_abs_log2_threshold: float = 1.00
    pathway_support_policy_id: str = "pathway-support-count-v1"
    weak_pathway_support_min_count: int = 1
    moderate_pathway_support_min_count: int = 2
    strong_pathway_support_min_count: int = 4
    classification_performed: bool = False
    sequence_targetability_override: bool = False
    missing_pathway_evidence_interpretation: Literal["unresolved_not_negative"] = (
        "unresolved_not_negative"
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> ResidualAttributionPolicyV1:
        if self.numerical_tolerance <= 0:
            raise ValueError("residual_attribution.numerical_tolerance must be positive")
        if self.negligible_residual_abs_log2_threshold < 0:
            raise ValueError("negligible residual threshold must be non-negative")
        if self.moderate_residual_abs_log2_threshold <= self.negligible_residual_abs_log2_threshold:
            raise ValueError("moderate residual threshold must exceed negligible threshold")
        if self.strong_residual_abs_log2_threshold <= self.moderate_residual_abs_log2_threshold:
            raise ValueError("strong residual threshold must exceed moderate threshold")
        if self.classification_performed:
            raise ValueError("residual attribution must not perform final classification")
        if self.sequence_targetability_override:
            raise ValueError("residual attribution must not override sequence targetability")
        if not (
            0
            < self.weak_pathway_support_min_count
            <= self.moderate_pathway_support_min_count
            <= self.strong_pathway_support_min_count
        ):
            raise ValueError("pathway support count thresholds must be ordered and positive")
        return self

    @property
    def fingerprint(self) -> str:
        return stable_id("residual-attribution-policy", self.model_dump(mode="json"))


class GeneResidualAttributionEvidenceRecordV1(BaseModel):
    schema_version: str = "1"
    residual_attribution_record_id: str
    gene_id: str
    expected_direct_effect_record_id: str
    observed_normalized_log2fc: float
    expected_direct_effect_log2fc: float
    observed_vs_expected_log2_difference: float
    unresolved_residual_log2fc: float
    residual_abs_log2: float
    residual_direction: ResidualDirection
    residual_magnitude_status: ResidualMagnitudeStatus
    pathway_evidence_record_ids: tuple[str, ...] = ()
    pathway_support_count: int = 0
    pathway_support_summary: dict[str, object] = Field(default_factory=dict)
    residual_support_status: ResidualSupportStatus
    targetability_fields_preserved: dict[str, object] = Field(default_factory=dict)
    intended_target_calibration_value: float | None = None
    interpretation_boundary: str = INTERPRETATION_BOUNDARY
    warning_codes: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()
    source_expected_direct_effect_checksum: str | None = None
    source_pathway_evidence_checksum: str | None = None

    @model_validator(mode="after")
    def validate_boundary(self) -> GeneResidualAttributionEvidenceRecordV1:
        forbidden = {
            "_".join(("direct", "effect", "class")),
            "_".join(("secondary", "effect", "call")),
            "_".join(("mixed", "classification")),
            "_".join(("final", "classification")),
        }
        if forbidden.intersection(self.pathway_support_summary):
            raise ValueError("residual attribution output must not contain final call fields")
        return self


class ResidualAttributionUnresolvedRecordV1(BaseModel):
    schema_version: str = "1"
    unresolved_record_id: str
    gene_id: str
    reason: ResidualSupportStatus
    source_expected_direct_effect_record_id: str | None = None
    preserved_upstream_status: str | None = None
    warning_codes: tuple[str, ...] = ()


class ResidualAttributionRunRecordV1(BaseModel):
    schema_version: str = "1"
    run_id: str
    stage_name: Literal["residual_attribution"] = "residual_attribution"
    stage_version: str = "1.0"
    expected_direct_effect_result_id: str
    expected_direct_effect_checksum: str
    pathway_evidence_checksum: str | None = None
    policy_id: str
    policy_checksum: str
    started_at: str
    completed_at: str
    status: Literal["completed", "failed"]
    source_counts: dict[str, int] = Field(default_factory=dict)
    output_counts: dict[str, int] = Field(default_factory=dict)
    output_checksums: dict[str, str] = Field(default_factory=dict)
    verification_status: Literal["verified", "failed"]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class ResidualAttributionVerificationRecordV1(BaseModel):
    schema_version: str = "1"
    verification_id: str
    expected_direct_effect_checks: Literal["passed", "failed"]
    residual_preservation_checks: Literal["passed", "failed"]
    interpretation_boundary_checks: Literal["passed", "failed"]
    support_precedence_checks: Literal["passed", "failed"]
    artifact_reference_checks: Literal["passed", "failed"]
    count_reconciliation_checks: Literal["passed", "failed"]
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    verified_at: str


class ResidualAttributionResultV1(BaseModel):
    schema_version: str = "1"
    run_record: ResidualAttributionRunRecordV1
    policy_artifact: str
    gene_evidence_records_artifact: str
    unresolved_records_artifact: str
    summary_artifact: str
    verification_artifact: str
    warnings_artifact: str
    canonical_artifact_checksums: dict[str, str]
    counts: dict[str, int]
    status: Literal["completed", "failed"]
    interpretation_boundary: str = INTERPRETATION_BOUNDARY
    warnings: tuple[str, ...] = ()
